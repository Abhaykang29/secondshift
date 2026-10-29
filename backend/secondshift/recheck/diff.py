"""Re-check diff (spec section 9.11).

Matches previous CONFIRMED hazards to a new scan: same item found again =
STILL_PRESENT; area filmed and hazard gone (or safety object now found) =
RESOLVED; area not filmed = CANNOT_TELL; new confirmed items = NEW.
Score (documented): 100 - min(100, 2 x sum of open-hazard risk scores),
so clearing high-risk hazards moves the score the most.
Depends on: domain.hazards, pipeline.scan output.
"""

import uuid
from datetime import UTC, datetime

from secondshift.domain.enums import RecheckStatus, Verification
from secondshift.domain.hazards import Hazard, Recheck, RecheckItem
from secondshift.pipeline.scan import ScanOutput


def home_score(hazards: list[Hazard]) -> float:
    """The 0-100 home score for a set of hazards (open = not resolved)."""
    open_risk = sum(
        h.risk_score
        for h in hazards
        if h.verification in (Verification.CONFIRMED, Verification.NEEDS_HUMAN)
    )
    return round(max(0.0, 100.0 - min(100.0, 2.0 * open_risk)), 1)


def diff_scans(
    checkup_id: str,
    capture_id: str,
    previous: list[Hazard],
    new_output: ScanOutput,
    vision: object | None = None,
) -> Recheck:
    """Diff a previous hazard list against a fresh scan output.

    Pass 2 E.8: still_present items are contested by definition - the
    family says they fixed them. With a live provider, Spark judges
    them via prompts/recheck_judge.md (hazard text today; before/after
    crops join when real footage flows, Phase E verification). A
    "resolved" or "cannot_tell" verdict overrides, with the reason
    recorded; anything else keeps the deterministic status.
    """
    new_by_item = {h.item_id: h for h in new_output.hazards}
    items: list[RecheckItem] = []
    previous_items = set()
    for old in previous:
        if old.verification is not Verification.CONFIRMED:
            continue
        previous_items.add(old.item_id)
        new = new_by_item.get(old.item_id)
        before_kf = old.evidence.keyframe_ids[0] if old.evidence.keyframe_ids else None
        if new is not None and new.verification is Verification.CONFIRMED:
            status = RecheckStatus.STILL_PRESENT
            reason = "Found again in the new walkthrough."
            if vision is not None:
                verdict = vision.judge_recheck(old.title, None, None)  # type: ignore[attr-defined]
                if verdict and str(verdict.get("status")) in ("resolved", "cannot_tell"):
                    status = RecheckStatus(str(verdict["status"]))
                    reason = f"Judge: {verdict.get('reason', 'contested item re-judged.')}"
            items.append(
                RecheckItem(
                    hazard_id=old.id,
                    item_id=old.item_id,
                    room=old.room,
                    status=status,
                    reason=reason,
                    before_keyframe_id=before_kf,
                    after_keyframe_id=new.evidence.keyframe_ids[0]
                    if new.evidence.keyframe_ids
                    else None,
                )
            )
        elif old.room not in new_output.rooms_seen and new_output.rooms_seen:
            items.append(
                RecheckItem(
                    hazard_id=old.id,
                    item_id=old.item_id,
                    room=old.room,
                    status=RecheckStatus.CANNOT_TELL,
                    reason=f"The {old.room} was not filmed in the re-check.",
                    before_keyframe_id=before_kf,
                    after_keyframe_id=None,
                )
            )
        else:
            items.append(
                RecheckItem(
                    hazard_id=old.id,
                    item_id=old.item_id,
                    room=old.room,
                    status=RecheckStatus.RESOLVED,
                    reason="Not found in the new walkthrough, and the area was filmed.",
                    before_keyframe_id=before_kf,
                    after_keyframe_id=None,
                )
            )
    for new in new_output.hazards:
        if new.verification is Verification.CONFIRMED and new.item_id not in previous_items:
            items.append(
                RecheckItem(
                    hazard_id=None,
                    item_id=new.item_id,
                    room=new.room,
                    status=RecheckStatus.NEW,
                    reason="Found for the first time in the re-check.",
                    before_keyframe_id=None,
                    after_keyframe_id=new.evidence.keyframe_ids[0]
                    if new.evidence.keyframe_ids
                    else None,
                )
            )
    return Recheck(
        id=uuid.uuid4().hex,
        checkup_id=checkup_id,
        capture_id=capture_id,
        created_at=datetime.now(UTC),
        items=items,
        rule_outcomes=[],
        score_before=home_score(previous),
        score_after=home_score(new_output.hazards),
    )
