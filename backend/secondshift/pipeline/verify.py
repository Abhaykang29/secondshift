"""Localize and verify with SAM (spec section 9.5) - the core step.

Presence: SAM mask with score >= MIN_MASK_SCORE and plausible area on at
least one evidence frame confirms; otherwise the judge decides
needs_human vs rejected (sam_plus_judge mode).
Absence: anchor found + safety object not found + coverage = confirmed;
safety found = rejected; anchor not found = cannot_assess.
Measurement: compared/recorded only when a measurement exists.
Interaction: verified by the routine step; here it passes through as
needs_human until routine evidence attaches (scan.py upgrades it).
Depends on: providers.base, domain models, checklists.loader.
"""

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


def _area(mask: Mask) -> float:
    x0, y0, x1, y1 = mask.bbox
    return max(0.0, (x1 - x0)) * max(0.0, (y1 - y0))


def _plausible(mask: Mask, min_score: float) -> bool:
    return mask.score >= min_score and _MIN_AREA <= _area(mask) <= _MAX_AREA


def _item_for(packs: list[Pack], proposal: HazardProposal) -> tuple[Pack, PackItem]:
    for pack in packs:
        for item in pack.items:
            if item.id == proposal.item_id:
                return pack, item
    raise ValueError(f"Proposal references unknown item {proposal.item_id}")


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
    """Verify every proposal. Returns (hazards incl. rejected, cannot_assess)."""
    hazards: list[Hazard] = []
    cannot: list[CannotAssess] = []
    for idx, proposal in enumerate(proposals):
        pack, item = _item_for(packs, proposal)
        frames = _nearest_keyframes(keyframes, proposal.evidence_timestamps, verify_frames)
        evidence = Evidence(
            keyframe_ids=[f.id for f in frames],
            timestamps=[f.t for f in frames],
        )
        verification: Verification
        reason: str
        if verify_mode == "none":
            verification, reason = Verification.NEEDS_HUMAN, "Verification disabled (ablation)."
        elif item.kind is ItemKind.PRESENCE:
            masks: list[Mask] = []
            for frame in frames:
                masks.extend(
                    segmenter.segment(
                        ImageRef(path=frame.image_path, keyframe_id=frame.id, t=frame.t),
                        proposal.sam_prompts,
                    )
                )
            good = [m for m in masks if _plausible(m, min_mask_score)]
            evidence.masks = good
            if good:
                verification = Verification.CONFIRMED
                reason = f"Confirmed by SAM (mask score {max(m.score for m in good):.2f})."
            elif verify_mode == "sam":
                verification, reason = Verification.REJECTED, "SAM found no matching object."
            else:
                verdict = judge.judge(
                    JudgeRequest(
                        claim=f"{proposal.item_id}: {proposal.description}",
                        images=[ImageRef(path=f.image_path, keyframe_id=f.id) for f in frames],
                        context=f"sam_found: false; prompts: {proposal.sam_prompts}",
                    )
                )
                verification = Verification(verdict.verification)
                reason = verdict.reason
        elif item.kind is ItemKind.ABSENCE:
            anchor_masks: list[Mask] = []
            safety_masks: list[Mask] = []
            for frame in frames:
                ref = ImageRef(path=frame.image_path, keyframe_id=frame.id, t=frame.t)
                anchor_masks.extend(segmenter.segment(ref, proposal.sam_prompts))
                safety_masks.extend(segmenter.segment(ref, proposal.safety_prompts))
            evidence.masks = anchor_masks
            if safety_masks:
                verification = Verification.REJECTED
                reason = "The safety object is present in the evidence frames."
            elif anchor_masks:
                verification = Verification.CONFIRMED
                reason = "Anchor visible and no safety object found where it should be."
            else:
                verification = Verification.CANNOT_ASSESS
                reason = f"Didn't see the {proposal.sam_prompts[0] if proposal.sam_prompts else 'anchor'} clearly."
                cannot.append(
                    CannotAssess(
                        area=proposal.room,
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
                        area=proposal.room,
                        reason="needs_measurement",
                        detail=reason,
                    )
                )
        else:  # INTERACTION - routine step decides; start at needs_human
            verification = Verification.NEEDS_HUMAN
            reason = "Interaction item: decided by the routine-clip analysis."
        hazards.append(
            Hazard(
                id=f"hz-{idx:03d}-{proposal.item_id.lower()}",
                checkup_id=checkup_id,
                pack_id=pack.pack_id,
                item_id=proposal.item_id,
                kind=item.kind,
                room=proposal.room,
                title=item.title,
                description=proposal.description,
                why_it_matters=proposal.why_risky,
                severity=Severity(item.severity),
                verification=verification,
                verification_reason=reason,
                evidence=evidence,
                risk_score=0.0,
            )
        )
    return hazards, cannot
