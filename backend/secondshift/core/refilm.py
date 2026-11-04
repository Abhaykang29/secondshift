"""refilm: a short follow-up clip settles a previous check's
cannot-tell items and merges the answers into the SAME report.

Deliberately separate from recheck(): re-check films a LATER visit
and diffs two reports; re-film completes THIS visit. The follow-up
clip (<=60s) is scanned with a checklist containing only the
previous report's refilmable cannot-tell items; the merge keeps
everything else in the report untouched.
"""

import uuid
from pathlib import Path

from secondshift.capture.probe import probe_video
from secondshift.checklists.loader import Pack
from secondshift.config import Settings
from secondshift.core.check import _prepare_keyframes
from secondshift.domain.checkup import Checkup, Consent
from secondshift.domain.enums import CaptureKind
from secondshift.domain.hazards import Report
from secondshift.pipeline import refilm as refilm_mod
from secondshift.pipeline.scan import ScanInput, run_scan
from secondshift.privacy.blur import blur_and_drop_failed
from secondshift.providers.registry import Providers
from secondshift.storage.repository import Repository

MAX_REFILM_SECONDS = 60.0


def refilm(
    previous: Report,
    video_path: str,
    packs: list[Pack],  # the previous check's own packs
    providers: Providers,
    settings: Settings,
    work_dir: str,
    *,
    store: Repository | None = None,
) -> Report:
    """Run the follow-up clip and return the merged report.

    Raises ValueError when the clip is too long or the previous
    report has nothing a camera could settle.
    """
    probe = probe_video(video_path, max_minutes=settings.max_capture_minutes)
    if probe.duration_s > MAX_REFILM_SECONDS + 1.0:
        raise ValueError(
            f"Follow-up clips are at most 60 seconds; this one is "
            f"{probe.duration_s:.0f}s."
        )
    refilm_pack = refilm_mod.build_refilm_pack(previous, packs)
    if refilm_pack is None:
        raise ValueError(
            "Nothing in this report can be settled by filming - every "
            "unanswered item needs a person, not a camera."
        )
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    capture_id = uuid.uuid4().hex
    capture, keyframes = _prepare_keyframes(video_path, settings, work, capture_id)
    capture.checkup_id = previous.checkup_id
    capture.kind = CaptureKind.REFILM
    keyframes = blur_and_drop_failed(keyframes, providers.segmenter)
    transient = Checkup(
        id=previous.checkup_id,
        created_at=previous.generated_at,
        home_label="",
        resident_label="",
        pack_ids=[refilm_pack.pack_id],
        consent=Consent(resident_informed=True, no_private_moments=True),
    )
    output = run_scan(
        providers,
        ScanInput(
            checkup=transient,
            packs=[refilm_pack],
            keyframes=keyframes,
            sweep=True,
            verify_mode=settings.verify_mode,
        ),
    )
    merged = refilm_mod.merge_refilm(previous, output, packs)
    # Fresh guidance for whatever is still unsettled, from the
    # follow-up clip's own frames; keep the previous wording for any
    # item the generator could not cover.
    fresh = refilm_mod.generate_refilm_instructions(
        merged.cannot_assess, packs, keyframes, providers.vision
    )
    if fresh:
        fresh_ids = {ins.item_id for ins in fresh}
        merged.refilm_instructions = fresh + [
            ins for ins in merged.refilm_instructions if ins.item_id not in fresh_ids
        ]
    if store is not None:
        store.put("capture", capture_id, capture.model_dump(mode="json"))
        store.put(
            "keyframes",
            capture_id,
            {"keyframes": [kf.model_dump(mode="json") for kf in keyframes]},
        )
        store.put("report", previous.checkup_id, merged.model_dump(mode="json"))
    return merged
