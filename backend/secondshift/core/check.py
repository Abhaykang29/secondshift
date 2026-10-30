"""check / recheck: video + checklist -> verdicts with evidence.

check() runs the whole engine synchronously against a video file:
probe -> keyframes -> person blur -> propose + sweep -> verify ->
fixes -> visualizations -> report. It is the same pipeline the app
runs as a background job (pipeline.scan.run_scan_job), minus the
HTTP layer. recheck() runs a fresh check on a new video and diffs it
against the previous report (resolved / still there / new / can't
tell) via recheck.diff.diff_scans.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from secondshift.capture.extract import extract_frames
from secondshift.capture.keyframes import select_keyframes
from secondshift.capture.probe import probe_video
from secondshift.config import Settings
from secondshift.core.compile import Checklist
from secondshift.domain.checkup import Capture, Checkup, Consent
from secondshift.domain.enums import CaptureKind
from secondshift.domain.hazards import Recheck, Report
from secondshift.pipeline.scan import ScanInput, run_scan, run_scan_job
from secondshift.privacy.blur import blur_keyframes
from secondshift.providers.registry import Providers
from secondshift.recheck.diff import diff_scans
from secondshift.storage.repository import Repository


def _prepare_keyframes(
    video_path: str, settings: Settings, work_dir: Path, capture_id: str
) -> tuple[Capture, list]:  # type: ignore[type-arg]
    probe = probe_video(video_path, max_minutes=settings.max_capture_minutes)
    capture = Capture(
        id=capture_id,
        checkup_id="",
        kind=CaptureKind.WALKTHROUGH,
        file_path=video_path,
        duration_s=probe.duration_s,
        width=probe.width,
        height=probe.height,
        fps=probe.fps,
        source="phone_upload",
    )
    frames = extract_frames(video_path, str(work_dir / "frames"), settings.sample_fps)
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
    return capture, keyframes


def check(
    video_path: str,
    checklist: Checklist,
    providers: Providers,
    settings: Settings,
    work_dir: str,
    *,
    home_label: str = "Home",
    resident_label: str = "resident",
    store: Repository | None = None,
) -> Report:
    """Run a full check of one video against one checklist."""
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    checkup_id = uuid.uuid4().hex
    capture_id = uuid.uuid4().hex
    capture, keyframes = _prepare_keyframes(video_path, settings, work, capture_id)
    capture.checkup_id = checkup_id
    # Privacy first: blur people in every keyframe before any model
    # or report step reads them (same order as the app path).
    blur_keyframes([kf.image_path for kf in keyframes if kf.image_path], providers.segmenter)
    checkup = Checkup(
        id=checkup_id,
        created_at=datetime.now(UTC),
        home_label=home_label,
        resident_label=resident_label,
        pack_ids=[checklist.pack.pack_id],
        consent=Consent(resident_informed=True, no_private_moments=True),
    )
    scan_input = ScanInput(
        checkup=checkup,
        packs=[checklist.pack],
        keyframes=keyframes,
        sweep=True,
    )
    repo = store or Repository(work / "store.json")
    _job, report = run_scan_job(repo, providers, scan_input, data_dir=str(work))
    return report


def recheck(
    previous: Report,
    video_path: str,
    checklist: Checklist,
    providers: Providers,
    settings: Settings,
    work_dir: str,
    *,
    home_label: str = "Home",
    resident_label: str = "resident",
) -> Recheck:
    """Re-film, re-check, and diff against the previous report."""
    work = Path(work_dir)
    checkup_id = uuid.uuid4().hex
    capture_id = uuid.uuid4().hex
    _capture, keyframes = _prepare_keyframes(video_path, settings, work, capture_id)
    blur_keyframes([kf.image_path for kf in keyframes if kf.image_path], providers.segmenter)
    checkup = Checkup(
        id=checkup_id,
        created_at=datetime.now(UTC),
        home_label=home_label,
        resident_label=resident_label,
        pack_ids=[checklist.pack.pack_id],
        consent=Consent(resident_informed=True, no_private_moments=True),
    )
    output = run_scan(
        providers,
        ScanInput(
            checkup=checkup,
            packs=[checklist.pack],
            keyframes=keyframes,
            sweep=True,
        ),
    )
    return diff_scans(
        checkup_id,
        capture_id,
        previous.hazards,
        output,
        vision=providers.vision,
    )
