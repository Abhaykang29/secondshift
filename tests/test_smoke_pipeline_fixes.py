"""Smoke-test pipeline fixes (2026-10-29) - unit tests, no live calls.

Covers: batch-provenance timestamps (never a default 0.0), one-label
room classification, largest-and-most-central evidence selection,
couldn't-assess cleanup, the hidden-safety needs_human cap, the
absence edit region, SAM wording, the watermark glyph, and the rug
pack's evidence description.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondshift.checklists.loader import load_all_packs  # noqa: E402
from secondshift.domain.checkup import Keyframe  # noqa: E402
from secondshift.domain.enums import ItemKind, Severity, Verification  # noqa: E402
from secondshift.domain.hazards import (  # noqa: E402
    CannotAssess,
    Evidence,
    Hazard,
    HazardProposal,
    Mask,
    Visualization,
)
from secondshift.pipeline.propose import (  # noqa: E402
    clean_cannot_assess,
    propose_hazards,
)
from secondshift.pipeline.verify import verify_proposals  # noqa: E402
from secondshift.providers.base import ProposeResponse  # noqa: E402


def _kf(idx: int, t: float, room: str | None = None) -> Keyframe:
    return Keyframe(
        id=f"kf-{idx}",
        capture_id="cap",
        t=t,
        image_path="",
        sharpness=500.0,
        brightness=120.0,
        usable=True,
        room_guess=room,
    )


class _BatchVision:
    """Returns one canned response per batch, in order."""

    def __init__(self, responses: list[ProposeResponse]) -> None:
        self._responses = responses
        self._calls = 0

    def propose_hazards(self, req):  # type: ignore[no-untyped-def]
        response = self._responses[self._calls]
        self._calls += 1
        return response

    def classify_room(self, image):  # type: ignore[no-untyped-def]
        return None


def _proposal(item_id: str, timestamps: list[float], room: str = "unknown") -> HazardProposal:
    return HazardProposal(
        item_id=item_id,
        room=room,
        description="thing",
        evidence_timestamps=timestamps,
        sam_prompts=["thing"],
        safety_prompts=[],
        confidence=0.8,
        why_risky="risk",
    )


def test_omitted_timestamps_map_to_the_batch_frames() -> None:
    """No timestamps from the model -> provenance = the batch's frames,
    never a default 0.0; per-image room labels land on the keyframes."""
    packs = [load_all_packs()["falls_older_adults"]]
    keyframes = [_kf(0, 10.0), _kf(1, 10.5), _kf(2, 20.0), _kf(3, 20.5)]
    vision = _BatchVision(
        [
            ProposeResponse(
                proposals=[_proposal("FALL-FLOOR-RUG", [])],
                rooms_seen=["kitchen"],
                keyframe_rooms=["kitchen", "kitchen"],
            ),
            ProposeResponse(proposals=[], rooms_seen=[], keyframe_rooms=["bedroom", "bedroom"]),
        ]
    )
    proposals, _cannot, rooms_seen = propose_hazards(vision, packs, keyframes, [], [], batch_size=2)
    assert len(proposals) == 1
    assert proposals[0].evidence_timestamps == []
    assert proposals[0].source_keyframe_ids == ["kf-0", "kf-1"]
    assert proposals[0].room == "kitchen"  # unanimous batch room label
    assert [kf.room_guess for kf in keyframes] == ["kitchen", "kitchen", "bedroom", "bedroom"]
    assert rooms_seen == ["kitchen", "bedroom"]


def test_foreign_batch_timestamps_are_treated_as_omitted() -> None:
    """Timestamps like 0,1,2 that land on no frame in the proposal's own
    batch are not trusted - the batch provenance replaces them."""
    packs = [load_all_packs()["falls_older_adults"]]
    keyframes = [_kf(0, 30.0), _kf(1, 30.5)]
    vision = _BatchVision(
        [
            ProposeResponse(
                proposals=[_proposal("FALL-FLOOR-RUG", [0.0, 1.0, 2.0])],
                keyframe_rooms=["living", "living"],
            )
        ]
    )
    proposals, _cannot, _rooms = propose_hazards(vision, packs, keyframes, [], [], batch_size=2)
    assert proposals[0].evidence_timestamps == []
    assert proposals[0].source_keyframe_ids == ["kf-0", "kf-1"]


def test_model_timestamps_snap_to_real_keyframe_times() -> None:
    """Whole-second model timestamps snap to the actual keyframe times."""
    packs = [load_all_packs()["falls_older_adults"]]
    keyframes = [_kf(0, 10.0), _kf(1, 10.5), _kf(2, 11.0)]
    vision = _BatchVision(
        [
            ProposeResponse(
                proposals=[_proposal("FALL-FLOOR-RUG", [10.0, 11.0])],
                keyframe_rooms=["living", "living", "living"],
            )
        ]
    )
    proposals, _c, _r = propose_hazards(vision, packs, keyframes, [], [], batch_size=3)
    assert proposals[0].evidence_timestamps == [10.0, 11.0]
    assert proposals[0].source_keyframe_ids == ["kf-0", "kf-2"]


def _hazard(item_id: str, verification: Verification) -> Hazard:
    return Hazard(
        id=f"hz-{item_id}",
        checkup_id="c1",
        pack_id="falls_older_adults",
        item_id=item_id,
        kind=ItemKind.PRESENCE,
        room="living",
        title="t",
        description="d",
        why_it_matters="w",
        severity=Severity.HIGH,
        verification=verification,
        verification_reason="r",
        evidence=Evidence(keyframe_ids=[], timestamps=[]),
        risk_score=1.0,
    )


def test_clean_cannot_assess_dedupes_and_drops_verdicts_and_seen_rooms() -> None:
    """Fix 3: dedupe; drop items with a verdict; drop rooms in rooms_seen."""
    entries = [
        CannotAssess(area="bathroom", reason="not_filmed", detail="x"),
        CannotAssess(area="bathroom", reason="not_filmed", detail="x again"),
        CannotAssess(area="FALL-BED-LIGHT-REACH", reason="not_filmed", detail="y"),
        CannotAssess(area="FALL-BATH-GRAB-MISSING", reason="not_filmed", detail="z"),
        CannotAssess(area="stairs", reason="not_filmed", detail="s"),
    ]
    hazards = [_hazard("FALL-BED-LIGHT-REACH", Verification.REJECTED)]
    cleaned = clean_cannot_assess(entries, hazards, rooms_seen=["bathroom", "living"])
    areas = [c.area for c in cleaned]
    assert areas == ["FALL-BATH-GRAB-MISSING", "stairs"]


class _TwoFrameSeg:
    """SAM stub: a big edge box on kf-a, a slightly smaller centred box on kf-b."""

    def segment(self, image, prompts):  # type: ignore[no-untyped-def]
        if image.keyframe_id == "kf-a":
            return [
                Mask(keyframe_id="kf-a", bbox=(0.0, 0.25, 0.55, 0.75), score=0.9, prompt=prompts[0])
            ]
        return [Mask(keyframe_id="kf-b", bbox=(0.3, 0.3, 0.8, 0.8), score=0.9, prompt=prompts[0])]

    def segment_video(self, frames, prompts):  # type: ignore[no-untyped-def]
        return {}


class _Judge:
    def judge(self, req):  # type: ignore[no-untyped-def]
        from secondshift.providers.base import JudgeResponse

        return JudgeResponse(verification="needs_human", reason="judge")


def test_evidence_frame_is_the_largest_most_central_sam_frame() -> None:
    """Fix 2: one evidence frame - the centred box beats the bigger edge
    box - and the SAM wording carries no mask score."""
    packs = [load_all_packs()["falls_older_adults"]]
    proposal = _proposal("FALL-FLOOR-RUG", [1.0, 2.0], room="living")
    frames = [_kf(0, 1.0), _kf(1, 2.0)]
    frames[0].id, frames[1].id = "kf-a", "kf-b"
    hazards, _ = verify_proposals(_TwoFrameSeg(), _Judge(), packs, [proposal], frames, [], "c1")
    hazard = hazards[0]
    assert hazard.verification is Verification.CONFIRMED
    assert hazard.verification_reason == "Found by SAM (box)."
    assert hazard.evidence.keyframe_ids == ["kf-b"]
    assert hazard.evidence.timestamps == [2.0]
    assert len(hazard.evidence.masks) == 1
    assert hazard.evidence.masks[0].keyframe_id == "kf-b"


class _AnchorSeg:
    """SAM stub for absence items: anchor found, safety object absent -
    unless the prompt is the safety prompt for the 'present' variant."""

    def __init__(self, safety_present: bool = False) -> None:
        self.safety_present = safety_present

    def segment(self, image, prompts):  # type: ignore[no-untyped-def]
        joined = " ".join(prompts).lower()
        if any(
            word in joined
            for word in (
                "extinguisher",
                "carbon monoxide",
                "co alarm",
                "anti-tip",
                "wall anchor",
                "grab bar",
            )
        ):
            if self.safety_present:
                return [
                    Mask(
                        keyframe_id=image.keyframe_id or "k",
                        bbox=(0.4, 0.4, 0.5, 0.6),
                        score=0.9,
                        prompt=prompts[0],
                    )
                ]
            return []
        return [
            Mask(
                keyframe_id=image.keyframe_id or "k",
                bbox=(0.1, 0.1, 0.6, 0.6),
                score=0.9,
                prompt=prompts[0],
            )
        ]

    def segment_video(self, frames, prompts):  # type: ignore[no-untyped-def]
        return {}


def _absence_proposal(item_id: str, sam: list[str], safety: list[str]) -> HazardProposal:
    return HazardProposal(
        item_id=item_id,
        room="kitchen",
        description="d",
        evidence_timestamps=[1.0],
        sam_prompts=sam,
        safety_prompts=safety,
        confidence=0.8,
        why_risky="w",
    )


def test_hidden_safety_objects_cap_at_needs_human() -> None:
    """Fix 5: extinguisher, CO alarm and anti-tip strap can never be
    'confirmed missing' from video - they may be stored out of sight."""
    frames = [_kf(0, 1.0)]
    cases = [
        (
            "fire_safety",
            _absence_proposal("FIRE-EXTINGUISHER-ABSENT", ["stove"], ["fire extinguisher"]),
        ),
        (
            "fire_safety",
            _absence_proposal("FIRE-CO-ALARM-ABSENT", ["hallway"], ["carbon monoxide alarm"]),
        ),
        (
            "babyproofing",
            _absence_proposal("BABY-TIPOVER-FURNITURE", ["dresser"], ["anti-tip strap"]),
        ),
    ]
    for pack_id, proposal in cases:
        packs = [load_all_packs()[pack_id]]
        hazards, _ = verify_proposals(_AnchorSeg(), _Judge(), packs, [proposal], frames, [], "c1")
        assert hazards[0].verification is Verification.NEEDS_HUMAN, proposal.item_id
        assert hazards[0].verification_reason == "Not visible, may be stored out of sight."


def test_visible_safety_absence_still_confirms() -> None:
    """A grab bar is not a hidden object: anchor + no bar still confirms."""
    packs = [load_all_packs()["falls_older_adults"]]
    proposal = _absence_proposal("FALL-BATH-GRAB-MISSING", ["toilet"], ["grab bar"])
    hazards, _ = verify_proposals(
        _AnchorSeg(), _Judge(), packs, [proposal], [_kf(0, 1.0)], [], "c1"
    )
    assert hazards[0].verification is Verification.CONFIRMED


def test_absence_edit_region_is_not_a_thin_strip() -> None:
    """Fix 1: the extinguisher case - a thin wide anchor at the top edge
    must yield a substantial placement region that does not overlap it."""
    from secondshift.pipeline.visualize import _region_for

    hazard = Hazard(
        id="hz-x",
        checkup_id="c1",
        pack_id="fire_safety",
        item_id="FIRE-EXTINGUISHER-ABSENT",
        kind=ItemKind.ABSENCE,
        room="kitchen",
        title="t",
        description="d",
        why_it_matters="w",
        severity=Severity.MEDIUM,
        verification=Verification.NEEDS_HUMAN,
        verification_reason="r",
        evidence=Evidence(
            keyframe_ids=["k"],
            timestamps=[11.0],
            masks=[
                Mask(
                    keyframe_id="k",
                    bbox=(0.712, 0.021, 0.999, 0.069),
                    score=0.9,
                    prompt="kitchen counter",
                )
            ],
        ),
        risk_score=1.0,
    )
    region = _region_for(hazard, 1920, 1080)
    assert region is not None
    x0, y0, x1, y1 = region
    assert (x1 - x0) >= 0.18 * 1920
    assert (y1 - y0) >= 0.20 * 1080
    # No overlap with the anchor box in pixels.
    ax0, ay0, ax1, ay1 = 0.712 * 1920, 0.021 * 1080, 0.999 * 1920, 0.069 * 1080
    assert x1 <= ax0 or x0 >= ax1 or y1 <= ay0 or y0 >= ay1


def test_absence_region_shrinks_for_a_frame_filling_anchor() -> None:
    """A bed-sized anchor leaves only the wall above it: the region
    search scales down and finds that free area instead of giving up
    or painting over the anchor."""
    from secondshift.pipeline.visualize import _region_for

    hazard = Hazard(
        id="hz-y",
        checkup_id="c1",
        pack_id="falls_older_adults",
        item_id="FALL-BED-LIGHT-REACH",
        kind=ItemKind.ABSENCE,
        room="bedroom",
        title="t",
        description="d",
        why_it_matters="w",
        severity=Severity.MEDIUM,
        verification=Verification.CONFIRMED,
        verification_reason="r",
        evidence=Evidence(
            keyframe_ids=["k"],
            timestamps=[46.5],
            masks=[
                Mask(keyframe_id="k", bbox=(0.144, 0.345, 0.818, 0.999), score=0.9, prompt="bed")
            ],
        ),
        risk_score=1.0,
    )
    region = _region_for(hazard, 1920, 1080)
    assert region is not None
    x0, y0, x1, y1 = region
    assert (x1 - x0) >= 100 and (y1 - y0) >= 100
    ax0, ay0, ax1, ay1 = 0.144 * 1920, 0.345 * 1080, 0.818 * 1920, 0.999 * 1080
    assert x1 <= ax0 or x0 >= ax1 or y1 <= ay0 or y0 >= ay1


def test_watermark_uses_a_plain_hyphen() -> None:
    """Fix 7: no em dash glyph anywhere in the watermark path."""
    from secondshift.pipeline.visualize import WATERMARK

    assert WATERMARK == "Visualization - not a photo"
    viz = Visualization(
        id="v1",
        hazard_id="hz-x",
        source_keyframe_id="k",
        image_path="viz.png",
        prompt_used="p",
    )
    assert viz.watermark == "Visualization - not a photo"


def test_rug_pack_evidence_excludes_large_furniture_held_rugs() -> None:
    """Fix 9: the falls pack's rug evidence names small loose rugs/mats
    and excludes large furniture-held area rugs without curled edges."""
    pack = load_all_packs()["falls_older_adults"]
    rug = next(item for item in pack.items if item.id == "FALL-FLOOR-RUG")
    evidence = rug.observable_evidence.lower()
    assert "small" in evidence and "loose" in evidence
    assert "large area rug" in evidence and "curled" in evidence


def test_labeled_propose_payload_carries_real_timestamps() -> None:
    """The propose payload labels each image with its real timestamp -
    the model is never left to guess t=0, 1, 2..."""
    from secondshift.providers.meta.text_vision import build_propose_payload

    keyframes = [_kf(0, 4.0), _kf(1, 5.5)]
    for kf in keyframes:
        kf.image_path = __file__  # any readable file stands in for a frame
    payload = build_propose_payload("prompt", keyframes, "fast")
    content = payload["messages"][0]["content"]
    texts = [part["text"] for part in content if part.get("type") == "text"]
    assert any("timestamp_seconds=4" in t for t in texts)
    assert any("timestamp_seconds=5.5" in t for t in texts)
    images = [part for part in content if part.get("type") == "image_url"]
    assert len(images) == 2


def test_blur_keyframes_runs_in_parallel_and_blurs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Fix 8 (blur leg): the batch blur helper processes every frame."""
    import cv2
    import numpy as np
    from secondshift.privacy.blur import blur_keyframes

    class PersonSeg:
        def segment(self, image, prompts):  # type: ignore[no-untyped-def]
            return [
                Mask(
                    keyframe_id=image.keyframe_id or "k",
                    bbox=(0.05, 0.05, 0.45, 0.95),
                    score=0.9,
                    prompt="person",
                )
            ]

        def segment_video(self, frames, prompts):  # type: ignore[no-untyped-def]
            return {}

    paths = []
    for i in range(3):
        frame = (np.random.RandomState(i).rand(100, 100, 3) * 255).astype(np.uint8)
        path = tmp_path / f"kf{i}.png"
        cv2.imwrite(str(path), frame)
        paths.append(str(path))
    assert blur_keyframes(paths, PersonSeg()) == [1, 1, 1]
