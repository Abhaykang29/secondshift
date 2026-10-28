"""Captures router: upload a video, probe/extract/select keyframes.

Phase 1 scope (spec section 9.1-9.2): an upload is probed, frames are
extracted at SAMPLE_FPS, keyframes are selected and stored. The scan
pipeline itself is Phase 2 (POST /checkups/{id}/scan).
Depends on: capture/*, domain.checkup, storage.
"""

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from secondshift.capture.extract import extract_audio, extract_frames
from secondshift.capture.keyframes import select_keyframes
from secondshift.capture.probe import CaptureTooLong, probe_video
from secondshift.domain.checkup import Capture
from secondshift.domain.enums import CaptureKind

router = APIRouter(tags=["captures"])


@router.post("/checkups/{checkup_id}/captures")
async def upload_capture(
    checkup_id: str,
    request: Request,
    file: UploadFile = File(...),  # noqa: B008 - FastAPI upload pattern
    kind: str = Form("walkthrough"),
    source: str = Form("phone_upload"),
) -> dict[str, Any]:
    """Upload one capture video and run Phase 1 processing on it."""
    store = request.app.state.store
    settings = request.app.state.settings
    if store.get("checkup", checkup_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown checkup {checkup_id}")
    capture_id = uuid.uuid4().hex
    base = Path(settings.data_dir) / checkup_id / capture_id
    base.mkdir(parents=True, exist_ok=True)
    video_path = base / f"capture{Path(file.filename or 'video.mp4').suffix or '.mp4'}"
    video_path.write_bytes(await file.read())
    try:
        probe = probe_video(str(video_path), max_minutes=settings.max_capture_minutes)
    except CaptureTooLong as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    capture = Capture(
        id=capture_id,
        checkup_id=checkup_id,
        kind=CaptureKind(kind),
        file_path=str(video_path),
        duration_s=probe.duration_s,
        width=probe.width,
        height=probe.height,
        fps=probe.fps,
        source=source,  # type: ignore[arg-type]
    )
    frames = extract_frames(str(video_path), str(base / "frames"), settings.sample_fps)
    keyframes = select_keyframes(
        frames,
        capture_id,
        settings.sample_fps,
        sharpness_min=settings.sharpness_min,
        brightness_min=settings.brightness_min,
        brightness_max=settings.brightness_max,
        change_min=settings.scene_change_min / 16,
        max_gap_s=settings.max_gap_s,
        max_keyframes=settings.max_keyframes,
    )
    audio_path = extract_audio(str(video_path), str(base / "narration.wav"))
    store.put("capture", capture_id, capture.model_dump(mode="json"))
    store.put(
        "keyframes", capture_id, {"keyframes": [k.model_dump(mode="json") for k in keyframes]}
    )
    if audio_path is not None:
        store.put("audio", capture_id, {"audio_path": str(audio_path)})
    return {
        **capture.model_dump(mode="json"),
        "keyframe_count": len(keyframes),
        "usable_keyframes": sum(1 for k in keyframes if k.usable),
    }


@router.get("/captures/{capture_id}/keyframes")
def get_keyframes(capture_id: str, request: Request) -> dict[str, Any]:
    """Return the selected keyframes for one capture."""
    found: dict[str, Any] | None = request.app.state.store.get("keyframes", capture_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"Unknown capture {capture_id}")
    return found
