"""Localize and verify with SAM (spec section 9.5) - the core step.

Presence: SAM mask with score >= MIN_MASK_SCORE and plausible area on at
least one evidence frame confirms; otherwise the judge decides
needs_human vs rejected (sam_plus_judge mode).
Absence: anchor found + safety object not found + coverage = confirmed;
safety found = rejected; anchor not found = cannot_assess.
Measurement: compared/recorded only when a measurement exists.
Interaction: verified by the routine step; here it passes through as
needs_human until routine evidence attaches (scan.py upgrades it).

Smoke-test fixes (2026-10-29):
- Evidence is ONE frame: the frame whose SAM box is largest and most
  central. That frame's id/timestamp/mask - and only that one - is what
  verification, the report and the after-photo all use.
- A proposal with no usable timestamps searches the batch frames in
  its source_keyframe_ids provenance; it never falls back to t=0.
- Hidden safety objects (fire extinguisher, CO alarm, anti-tip strap)
  cap at needs_human: "not visible, may be stored out of sight."
- Proposals verify in parallel (SAM and judge calls included), order
  preserved, within the transport's per-model rate limits.
Depends on: providers.base, domain models, checklists.loader.
"""

import math
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from secondshift.checklists.loader import Pack, PackItem
from secondshift.domain.checkup import Keyframe, Measurement
from secondshift.domain.enums import ItemKind, Severity, Verification
from secondshift.domain.hazards import (
    CannotAssess,
    Evidence,
    Hazard,
    HazardProposal,
    Mask,
)
from secondshift.providers.base import ImageRef, JudgeRequest, Segmenter, VisionReasoner

_MIN_AREA, _MAX_AREA = 0.001, 0.60

# Safety objects that are legitimately stored out of sight. Not seeing
# one on camera can never confirm it is missing (smoke-test fix 5).
HIDDEN_SAFETY_ITEMS = {
    "FIRE-EXTINGUISHER-ABSENT",
    "FIRE-CO-ALARM-ABSENT",
    "BABY-TIPOVER-FURNITURE",  # the anti-tip strap lives behind furniture
}
HIDDEN_SAFETY_REASON = "Not visible, may be stored out of sight."


def _nearest_keyframes(
    keyframes: list[Keyframe], timestamps: list[float], limit: int
) -> list[Keyframe]:
    chosen: list[Keyframe] = []
    for t in timestamps:
        if keyframes:
            nearest = min(keyframes, key=lambda k: abs(k.t - t))
            if nearest not in chosen:
                chosen.append(nearest)
        if len(chosen) >= limit:
            break
    return chosen


def _candidate_frames(
    keyframes: list[Keyframe], proposal: HazardProposal, verify_frames: int
) -> tuple[list[Keyframe], list[Keyframe]]:
    """Frames to search, and the smaller set used for judge/evidence.

    With usable timestamps: the nearest frames (<= verify_frames).
    Without: the proposal's batch provenance frames - all of them for
    the SAM search, an even spread of verify_frames for the judge.
    """
    by_id = {kf.id: kf for kf in keyframes}
    source = [by_id[kf_id] for kf_id in proposal.source_keyframe_ids if kf_id in by_id]
    pool = source or keyframes
    if proposal.evidence_timestamps:
        chosen = _nearest_keyframes(pool, proposal.evidence_timestamps, verify_frames)
        return chosen, chosen
    if source:
        if len(source) <= verify_frames:
            return source, source
        step = len(source) / verify_frames
        spread = [source[int(i * step)] for i in range(verify_frames)]
        return source, spread
    return [], []


def _area(mask: Mask) -> float:
    x0, y0, x1, y1 = mask.bbox
    return max(0.0, (x1 - x0)) * max(0.0, (y1 - y0))


def _plausible(mask: Mask, min_score: float) -> bool:
    return mask.score >= min_score and _MIN_AREA <= _area(mask) <= _MAX_AREA


def _evidence_score(mask: Mask) -> float:
    """Largest-and-most-central ranking for SAM boxes.

    Area dominates; a box at the frame centre gets up to a 2x boost
    over an equal box pushed into a corner.
    """
    x0, y0, x1, y1 = mask.bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    distance = math.hypot(cx - 0.5, cy - 0.5) / math.hypot(0.5, 0.5)
    return _area(mask) * (1.0 - 0.5 * min(1.0, distance))


def _best_mask(masks: list[Mask]) -> Mask | None:
    return max(masks, key=_evidence_score) if masks else None


def _room_for(frames: list[Keyframe], fallback: str) -> str:
    """The one-label room for a set of frames (mode of room_guess)."""
    rooms = [f.room_guess for f in frames if f.room_guess]
    if rooms:
        return Counter(rooms).most_common(1)[0][0]
    return fallback


def _item_for(packs: list[Pack], proposal: HazardProposal) -> tuple[Pack, PackItem]:
    for pack in packs:
        for item in pack.items:
            if item.id == proposal.item_id:
                return pack, item
    raise ValueError(f"Proposal references unknown item {proposal.item_id}")


def _verify_one(
    idx: int,
    proposal: HazardProposal,
    *,
    segmenter: Segmenter,
    judge: VisionReasoner,
    packs: list[Pack],
    keyframes: list[Keyframe],
    measurements: list[Measurement],
    checkup_id: str,
    verify_mode: str,
    verify_frames: int,
    min_mask_score: float,
) -> tuple[Hazard, list[CannotAssess]]:
    pack, item = _item_for(packs, proposal)
    search_frames, judge_frames = _candidate_frames(keyframes, proposal, verify_frames)
    evidence = Evidence(
        keyframe_ids=[f.id for f in judge_frames],
        timestamps=[f.t for f in judge_frames],
    )
    room = _room_for(judge_frames or search_frames, proposal.room)
    cannot: list[CannotAssess] = []
    verification: Verification
    reason: str

    def _select(mask: Mask | None) -> None:
        """Collapse evidence to the single selected SAM frame."""
        if mask is None:
            return
        frame = next((f for f in keyframes if f.id == mask.keyframe_id), None)
        if frame is None:
            return
        evidence.keyframe_ids = [frame.id]
        evidence.timestamps = [frame.t]
        evidence.masks = [mask]
        nonlocal_room[0] = frame.room_guess or room

    nonlocal_room = [room]

    if verify_mode == "none":
        verification, reason = Verification.NEEDS_HUMAN, "Verification disabled (ablation)."
    elif not search_frames and item.kind in (ItemKind.PRESENCE, ItemKind.ABSENCE):
        verification = Verification.CANNOT_ASSESS
        reason = "No evidence frames were supplied for this finding."
        cannot.append(CannotAssess(area=proposal.item_id, reason="not_filmed", detail=reason))
    elif item.kind is ItemKind.PRESENCE:
        masks: list[Mask] = []
        for frame in search_frames:
            masks.extend(
                segmenter.segment(
                    ImageRef(path=frame.image_path, keyframe_id=frame.id, t=frame.t),
                    proposal.sam_prompts,
                )
            )
        candidate_ids = {f.id for f in search_frames}
        good = [
            m for m in masks if m.keyframe_id in candidate_ids and _plausible(m, min_mask_score)
        ]
        selected = _best_mask(good)
        if selected is not None:
            _select(selected)
        if good and item.needs_human_unless:
            # The object is there, but the hazard depends on a detail
            # a mask can't prove (e.g. standing water in a bucket).
            # Only the judge, asked about that exact detail on the
            # SELECTED evidence frame, may confirm; otherwise a human
            # must look (mosquito pack).
            detail = item.needs_human_unless
            selected_frame = next((f for f in keyframes if f.id == evidence.keyframe_ids[0]), None)
            if verify_mode == "sam_plus_judge" and selected_frame is not None:
                verdict = judge.judge(
                    JudgeRequest(
                        claim=f"{proposal.item_id}: is {detail} clearly visible?",
                        images=[
                            ImageRef(
                                path=selected_frame.image_path,
                                keyframe_id=selected_frame.id,
                            )
                        ],
                        context=(
                            f"sam_found: true; detail_check: {detail}. Confirm ONLY "
                            "if the detail itself is clearly visible in the frame."
                        ),
                    )
                )
                if verdict.verification == "confirmed":
                    verification = Verification.CONFIRMED
                    reason = f"Found by SAM (box); the judge could clearly see: {detail}."
                else:
                    verification = Verification.NEEDS_HUMAN
                    reason = (
                        f"SAM found it, but {detail} isn't clearly visible - a person should check."
                    )
            else:
                verification = Verification.NEEDS_HUMAN
                reason = (
                    f"SAM found it, but {detail} can't be confirmed from a mask - "
                    "a person should check."
                )
        elif good:
            verification = Verification.CONFIRMED
            reason = "Found by SAM (box)."
        elif verify_mode == "sam":
            verification, reason = Verification.REJECTED, "SAM found no matching object."
        else:
            verdict = judge.judge(
                JudgeRequest(
                    claim=f"{proposal.item_id}: {proposal.description}",
                    images=[ImageRef(path=f.image_path, keyframe_id=f.id) for f in judge_frames],
                    context=f"sam_found: false; prompts: {proposal.sam_prompts}",
                )
            )
            verification = Verification(verdict.verification)
            reason = verdict.reason
    elif item.kind is ItemKind.ABSENCE:
        anchor_masks: list[Mask] = []
        safety_masks: list[Mask] = []
        for frame in search_frames:
            ref = ImageRef(path=frame.image_path, keyframe_id=frame.id, t=frame.t)
            anchor_masks.extend(segmenter.segment(ref, proposal.sam_prompts))
            safety_masks.extend(segmenter.segment(ref, proposal.safety_prompts))
        candidate_ids = {f.id for f in search_frames}
        anchor_masks = [m for m in anchor_masks if m.keyframe_id in candidate_ids]
        safety_masks = [m for m in safety_masks if m.keyframe_id in candidate_ids]
        if safety_masks:
            verification = Verification.REJECTED
            reason = "The safety object is present in the evidence frames."
            _select(_best_mask(safety_masks))
        elif anchor_masks:
            _select(_best_mask(anchor_masks))
            if proposal.item_id in HIDDEN_SAFETY_ITEMS:
                verification = Verification.NEEDS_HUMAN
                reason = HIDDEN_SAFETY_REASON
            else:
                verification = Verification.CONFIRMED
                reason = "Anchor visible and no safety object found where it should be."
        else:
            verification = Verification.CANNOT_ASSESS
            reason = (
                f"Didn't see the {proposal.sam_prompts[0] if proposal.sam_prompts else 'anchor'}"
                " clearly."
            )
            cannot.append(
                CannotAssess(
                    area=proposal.item_id,
                    reason="not_visible_by_design",
                    detail=reason,
                )
            )
    elif item.kind is ItemKind.MEASUREMENT:
        match = next(
            (
                m
                for m in measurements
                if any(word in m.label.lower() for word in item.title.lower().split())
                or "toilet" in m.label.lower()
            ),
            None,
        )
        if match is not None:
            evidence.measurement_ids = [match.id]
            verification = Verification.CONFIRMED
            reason = (
                f"Recorded: {match.value:g} {match.unit} - ask a professional "
                "whether this is too low."
            )
        else:
            verification = Verification.CANNOT_ASSESS
            reason = "No measurement was entered for this item."
            cannot.append(
                CannotAssess(
                    area=proposal.item_id,
                    reason="needs_measurement",
                    detail=reason,
                )
            )
    else:  # INTERACTION - routine step decides; start at needs_human
        verification = Verification.NEEDS_HUMAN
        reason = "Interaction item: decided by the routine-clip analysis."
    hazard = Hazard(
        id=f"hz-{idx:03d}-{proposal.item_id.lower()}",
        checkup_id=checkup_id,
        pack_id=pack.pack_id,
        item_id=proposal.item_id,
        kind=item.kind,
        room=nonlocal_room[0],
        title=item.title,
        description=proposal.description,
        why_it_matters=proposal.why_risky,
        severity=Severity(item.severity),
        verification=verification,
        verification_reason=reason,
        evidence=evidence,
        risk_score=0.0,
    )
    return hazard, cannot


def verify_proposals(
    segmenter: Segmenter,
    judge: VisionReasoner,
    packs: list[Pack],
    proposals: list[HazardProposal],
    keyframes: list[Keyframe],
    measurements: list[Measurement],
    checkup_id: str,
    verify_mode: str = "sam_plus_judge",
    verify_frames: int = 3,
    min_mask_score: float = 0.5,
) -> tuple[list[Hazard], list[CannotAssess]]:
    """Verify every proposal. Returns (hazards incl. rejected, cannot_assess).

    Proposals verify in parallel (bounded at 8 workers); the transport
    throttle keeps each model within its rate limit. Result order is
    the proposal order, so hazard ids and ranking stay deterministic.
    """
    if not proposals:
        return [], []

    def _run(indexed: tuple[int, HazardProposal]) -> tuple[Hazard, list[CannotAssess]]:
        idx, proposal = indexed
        return _verify_one(
            idx,
            proposal,
            segmenter=segmenter,
            judge=judge,
            packs=packs,
            keyframes=keyframes,
            measurements=measurements,
            checkup_id=checkup_id,
            verify_mode=verify_mode,
            verify_frames=verify_frames,
            min_mask_score=min_mask_score,
        )

    with ThreadPoolExecutor(max_workers=min(8, len(proposals))) as pool:
        results = list(pool.map(_run, enumerate(proposals)))
    hazards = [hazard for hazard, _ in results]
    cannot = [entry for _, entries in results for entry in entries]
    return hazards, cannot
