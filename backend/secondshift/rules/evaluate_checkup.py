"""Check-up rule evaluation (spec section 9.13).

OBJECT_PRESENT / OBJECT_ABSENT run SAM over keyframes from the matching
area; OBJECT_STATE adds the judge's state call. Areas that were not
filmed clearly yield CANNOT_TELL, never a guess. Watch-only primitives
are reported as needing Watch mode.
Depends on: providers.base, domain.rules, domain.checkup.
"""

from datetime import UTC, datetime

from secondshift.domain.checkup import Keyframe
from secondshift.domain.enums import Outcome, Primitive
from secondshift.domain.hazards import Evidence
from secondshift.domain.rules import RuleOutcome, RuleSpec
from secondshift.providers.base import ImageRef, JudgeRequest, Segmenter, VisionReasoner
from secondshift.rules.validate import WATCH_ONLY

_STATE_JUDGE_CONTEXT = "state_check"


def evaluate_checkup_rule(
    spec: RuleSpec,
    segmenter: Segmenter,
    judge: VisionReasoner,
    keyframes: list[Keyframe],
    rooms_seen: list[str],
) -> RuleOutcome:
    """Evaluate one compiled rule against a check-up's keyframes."""
    evaluated_at = datetime.now(UTC)
    if any(cond.primitive in WATCH_ONLY for cond in spec.conditions):
        return RuleOutcome(
            rule_id=spec.id,
            outcome=Outcome.CANNOT_TELL,
            reason="Needs Watch mode.",
            evidence=None,
            evaluated_at=evaluated_at,
        )
    outcomes: list[RuleOutcome] = []
    for condition in spec.conditions:
        area = condition.area_hint or condition.anchor or ""
        area_filmed = not area or area in rooms_seen or not rooms_seen
        frames = keyframes[:6]
        refs = [ImageRef(path=k.image_path, keyframe_id=k.id, t=k.t) for k in frames]
        if condition.primitive is Primitive.OBJECT_PRESENT:
            masks = [m for ref in refs for m in segmenter.segment(ref, [condition.target or ""])]
            if masks:
                outcomes.append(
                    RuleOutcome(
                        rule_id=spec.id,
                        outcome=Outcome.MET,
                        reason=f"'{condition.target}' was found in the {area or 'home'}.",
                        evidence=Evidence(
                            keyframe_ids=[m.keyframe_id for m in masks], timestamps=[], masks=masks
                        ),
                        evaluated_at=evaluated_at,
                    )
                )
            elif area_filmed:
                outcomes.append(
                    RuleOutcome(
                        rule_id=spec.id,
                        outcome=Outcome.NOT_MET,
                        reason=f"'{condition.target}' was not found, and the area was filmed clearly.",
                        evidence=None,
                        evaluated_at=evaluated_at,
                    )
                )
            else:
                outcomes.append(
                    RuleOutcome(
                        rule_id=spec.id,
                        outcome=Outcome.CANNOT_TELL,
                        reason=f"The {area} was not filmed clearly.",
                        evidence=None,
                        evaluated_at=evaluated_at,
                    )
                )
        elif condition.primitive is Primitive.OBJECT_ABSENT:
            anchor_masks = [
                m for ref in refs for m in segmenter.segment(ref, [condition.anchor or ""])
            ]
            safety_masks = [
                m for ref in refs for m in segmenter.segment(ref, [condition.target or ""])
            ]
            if safety_masks:
                outcomes.append(
                    RuleOutcome(
                        rule_id=spec.id,
                        outcome=Outcome.MET,
                        reason=f"'{condition.target}' is present near the {condition.anchor}.",
                        evidence=Evidence(
                            keyframe_ids=[m.keyframe_id for m in safety_masks],
                            timestamps=[],
                            masks=safety_masks,
                        ),
                        evaluated_at=evaluated_at,
                    )
                )
            elif anchor_masks:
                outcomes.append(
                    RuleOutcome(
                        rule_id=spec.id,
                        outcome=Outcome.NOT_MET,
                        reason=f"The {condition.anchor} was seen but no {condition.target} was found.",
                        evidence=None,
                        evaluated_at=evaluated_at,
                    )
                )
            else:
                outcomes.append(
                    RuleOutcome(
                        rule_id=spec.id,
                        outcome=Outcome.CANNOT_TELL,
                        reason=f"The {condition.anchor} was not seen clearly.",
                        evidence=None,
                        evaluated_at=evaluated_at,
                    )
                )
        elif condition.primitive is Primitive.OBJECT_STATE:
            masks = [m for ref in refs for m in segmenter.segment(ref, [condition.target or ""])]
            if not masks:
                outcomes.append(
                    RuleOutcome(
                        rule_id=spec.id,
                        outcome=Outcome.CANNOT_TELL,
                        reason=f"'{condition.target}' was not visible.",
                        evidence=None,
                        evaluated_at=evaluated_at,
                    )
                )
            else:
                verdict = judge.judge(
                    JudgeRequest(
                        claim=f"{condition.target} is {condition.target_state}",
                        images=refs,
                        context=f"{_STATE_JUDGE_CONTEXT}; sam_found: true",
                    )
                )
                outcome = (
                    Outcome.MET if verdict.verification == "confirmed" else Outcome.CANNOT_TELL
                )
                outcomes.append(
                    RuleOutcome(
                        rule_id=spec.id,
                        outcome=outcome,
                        reason=verdict.reason,
                        evidence=Evidence(
                            keyframe_ids=[m.keyframe_id for m in masks], timestamps=[], masks=masks
                        ),
                        evaluated_at=evaluated_at,
                    )
                )
        else:
            outcomes.append(
                RuleOutcome(
                    rule_id=spec.id,
                    outcome=Outcome.CANNOT_TELL,
                    reason=f"Primitive {condition.primitive.value} is not evaluated in check-up mode.",
                    evidence=None,
                    evaluated_at=evaluated_at,
                )
            )
    if any(o.outcome is Outcome.CANNOT_TELL for o in outcomes):
        combined = next(o for o in outcomes if o.outcome is Outcome.CANNOT_TELL)
    elif all(o.outcome is Outcome.MET for o in outcomes):
        combined = outcomes[0]
    else:
        combined = next(o for o in outcomes if o.outcome is Outcome.NOT_MET)
    return RuleOutcome(
        rule_id=spec.id,
        outcome=combined.outcome,
        reason=combined.reason,
        evidence=combined.evidence,
        evaluated_at=evaluated_at,
    )
