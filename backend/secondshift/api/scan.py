"""Scan router: run a check-up scan and read its report.

Phase 2 wires the pipeline to the API. If the capture has stored
keyframes they are used; otherwise (demo/tests) keyframes are synthesized
from the mock scenario's timestamps so the demo flow works with no video.
Depends on: pipeline.scan, checklists.loader, storage.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from secondshift.domain.checkup import Checkup, Keyframe
from secondshift.pipeline.scan import ScanInput, run_scan_job

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scan"])

BLUR_FAILED_MESSAGE = (
    "We couldn't blur people in this video, so nothing was sent to Meta. "
    "Try again in a minute."
)


class ScanRequest(BaseModel):
    """Body for starting a scan."""

    capture_id: str | None = None
    scenario: str | None = None


def plain_scan_error(exc: BaseException | str) -> str:
    """Map any scan failure to a plain sentence: what happened and
    what to do. Raw provider/transport text never reaches the user."""
    text = str(exc).lower()
    if "couldn't blur people" in text:
        return BLUR_FAILED_MESSAGE
    if (
        "urlopen error" in text
        or "connection refused" in text
        or "connection reset" in text
        or "connection aborted" in text
        or "name or service not known" in text
        or "name resolution" in text
        or "network is unreachable" in text
        or "remote end closed" in text
        or "certificate" in text
        or "ssl" in text
        or "broken pipe" in text
    ):
        return (
            "Couldn't reach Meta's API - check your internet or firewall, "
            "then try again. Your video is saved - you don't need to film again."
        )
    if "429" in text or "rate limit" in text or "too many requests" in text:
        return (
            "Meta's AI service is busy right now (rate limit). Wait a minute "
            "or two, then tap Try again. Your video is saved - you don't "
            "need to film again."
        )
    if "timed out" in text or "timeout" in text:
        return (
            "The check took too long and stopped. Tap Try again. Your "
            "video is saved - you don't need to film again."
        )
    if (
        "http error 5" in text
        or "internal server error" in text
        or "bad gateway" in text
        or "service unavailable" in text
    ):
        return (
            "Meta's AI service had a problem while running this check. "
            "Wait a moment, then tap Try again. Your video is saved."
        )
    return (
        "The check stopped partway through. Tap Try again. Your video "
        "is saved - if it keeps failing, try a shorter video."
    )


def _failed_scan_response(store: Any, exc: BaseException) -> dict[str, Any]:
    """Persist a failed scan job and return the plain failure body.

    A scan must never surface as a raw 500 (2026-11-04: a transient
    provider error right after frame extraction did exactly that);
    the processing screen renders job_status/error and offers Try
    again against the same capture.
    """
    import uuid as _uuid

    job_id = _uuid.uuid4().hex
    message = plain_scan_error(exc)
    store.put(
        "job",
        job_id,
        {
            "id": job_id,
            "kind": "scan",
            "steps": ["scan", "fixes", "visualize", "assemble"],
            "completed_steps": [],
            "status": "failed",
            "error": message,
        },
    )
    return {"job_id": job_id, "job_status": "failed", "error": message, "report": None}


@router.post("/checkups/{checkup_id}/scan")
def start_scan(checkup_id: str, body: ScanRequest, request: Request) -> dict[str, Any]:
    """Run the scan pipeline for a checkup and return its report."""
    store = request.app.state.store
    raw = store.get("checkup", checkup_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Unknown checkup {checkup_id}")
    checkup = Checkup.model_validate(raw)
    from secondshift.checklists.resolve import resolve_packs

    packs = resolve_packs(store, checkup.pack_ids)
    keyframes: list[Keyframe] = []
    if body.capture_id:
        stored = store.get("keyframes", body.capture_id)
        if stored:
            keyframes = [Keyframe.model_validate(k) for k in stored["keyframes"]]
        if stored is not None and not keyframes:
            # The capture exists but frame selection produced nothing
            # (e.g. every sampled frame failed the quality gates).
            # Fail honestly here instead of crashing inside the scan.
            raise HTTPException(
                status_code=422,
                detail="This capture produced no usable frames, so it cannot be scanned.",
            )
    scenario = body.scenario
    if not keyframes:
        # Demo path: no real capture yet - keyframes at 5s intervals.
        scenario = scenario or (
            "baby_home_demo" if checkup.pack_ids == ["babyproofing"] else "parent_home_demo"
        )
        keyframes = [
            Keyframe(
                id=f"demo-kf-{i:03d}",
                capture_id="demo",
                t=float(i * 5),
                image_path="",
                sharpness=500.0,
                brightness=120.0,
                usable=True,
            )
            for i in range(20)
        ]
    # Pass 2 Phase E.4: person-blur every real keyframe BEFORE the scan
    # reads it (spec 14.3). Demo keyframes have no files and are skipped.
    # Fail closed (privacy, final fix pass 2026-11-04): a frame whose
    # blur failed (-1) is dropped from the scan - it must never be sent
    # to any Meta model. If every frame fails, the scan stops here
    # with a plain message, before any provider sees a frame.
    if keyframes and keyframes[0].image_path:
        from secondshift.privacy.blur import blur_keyframes

        real = [kf for kf in keyframes if kf.image_path]
        try:
            results = blur_keyframes(
                [kf.image_path for kf in real],
                request.app.state.providers.segmenter,
            )
        except Exception as exc:
            return _failed_scan_response(store, exc)
        failed_ids = {kf.id for kf, r in zip(real, results, strict=True) if r == -1}
        if failed_ids:
            logger.warning(
                "scan of checkup %s: dropped %d of %d frames whose person-blur failed",
                checkup_id,
                len(failed_ids),
                len(real),
            )
            keyframes = [kf for kf in keyframes if kf.id not in failed_ids]
            if not keyframes:
                return _failed_scan_response(store, RuntimeError(BLUR_FAILED_MESSAGE))
    if (
        scenario is not None
        and not body.capture_id
        and request.app.state.settings.provider.value != "mock"
    ):
        raise HTTPException(
            status_code=422,
            detail="The demo home runs in demo mode (make demo). "
            "With live providers, upload a real walkthrough instead.",
        )
    if scenario is None and request.app.state.settings.provider.value == "mock":
        scenario = "baby_home_demo" if checkup.pack_ids == ["babyproofing"] else "parent_home_demo"
    if scenario is not None:
        for provider in (
            request.app.state.providers.vision,
            request.app.state.providers.segmenter,
            request.app.state.providers.transcriber,
        ):
            if hasattr(provider, "scenario_name"):
                setattr(provider, "scenario_name", scenario)
    narration_facts = []
    try:
        from secondshift.capture.narration import extract_facts

        segments = request.app.state.providers.transcriber.transcribe("demo", checkup.language)
        narration_facts = extract_facts(segments)
    except Exception:
        narration_facts = []
    # Result cache (consistency pass, 2026-11-03): the same video
    # bytes + the same checklists + the same engine version return
    # the stored report unchanged, instantly - a judge re-uploading
    # a clip sees the identical answer. Live scans only (never the
    # mock/demo scenarios). ?dev=1 bypasses the lookup and refreshes
    # the entry; the UI exposes that only behind ?dev=1.
    cache_key: str | None = None
    if (
        scenario is None
        and body.capture_id
        and request.app.state.settings.provider.value != "mock"
    ):
        import hashlib
        import uuid as _uuid
        from pathlib import Path as _Path

        from secondshift.engine_version import result_cache_key

        capture_raw = store.get("capture", body.capture_id) or {}
        video_sha = capture_raw.get("video_sha256")
        if not video_sha and capture_raw.get("file_path"):
            try:
                video_sha = hashlib.sha256(
                    _Path(capture_raw["file_path"]).read_bytes()
                ).hexdigest()
            except OSError:
                video_sha = None
        if video_sha:
            cache_key = result_cache_key(
                video_sha,
                checkup.pack_ids,
                verify_mode=request.app.state.settings.verify_mode,
            )
            if request.query_params.get("dev") != "1":
                hit = store.get("result_cache", cache_key)
                if hit:
                    report_dict = hit["report"]
                    store.put("report", checkup_id, report_dict)
                    job_id = _uuid.uuid4().hex
                    store.put(
                        "job",
                        job_id,
                        {
                            "id": job_id,
                            "kind": "scan",
                            "steps": ["scan", "fixes", "visualize", "assemble"],
                            "completed_steps": ["scan", "fixes", "visualize", "assemble"],
                            "status": "done",
                            "error": None,
                        },
                    )
                    return {
                        "job_id": job_id,
                        "job_status": "done",
                        "report": report_dict,
                        "cached": True,
                    }
    scan_input = ScanInput(
        checkup=checkup,
        packs=packs,
        keyframes=keyframes,
        scenario_name=scenario,
        narration_facts=narration_facts,
        verify_mode=request.app.state.settings.verify_mode,
        sweep=scenario is None,
        stable_propose=request.app.state.settings.stable_propose,
    )
    try:
        job, report = run_scan_job(
            store,
            request.app.state.providers,
            scan_input,
            data_dir=request.app.state.settings.data_dir,
        )
    except Exception as exc:
        return _failed_scan_response(store, exc)
    if cache_key:
        from secondshift.engine_version import ENGINE_VERSION

        try:
            store.put(
                "result_cache",
                cache_key,
                {
                    "report": report.model_dump(mode="json"),
                    "checkup_id": checkup_id,
                    "engine_version": ENGINE_VERSION,
                },
            )
        except Exception:
            pass  # the scan succeeded; a cache write must not fail it
    return {"job_id": job.id, "job_status": job.status, "report": report.model_dump(mode="json")}


@router.get("/checkups/{checkup_id}/report")
def get_report(checkup_id: str, request: Request) -> dict[str, Any]:
    """Return the stored report for a checkup."""
    found: dict[str, Any] | None = request.app.state.store.get("report", checkup_id)
    if found is None:
        raise HTTPException(status_code=404, detail="No report yet - run a scan first.")
    return found


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> dict[str, Any]:
    """Return one job's status (processing page polling)."""
    found: dict[str, Any] | None = request.app.state.store.get("job", job_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {job_id}")
    if found.get("status") == "failed" and found.get("error"):
        # Jobs persisted before the plain-message fix carry raw
        # provider text; never hand that to the processing screen.
        return {**found, "error": plain_scan_error(str(found["error"]))}
    return found
