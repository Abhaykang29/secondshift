"""RuleSpec validator (spec section 9.12, Layer 2 validation).

Pure checks on a compiled spec: allowed primitives only, at most 2
conditions, watch-only primitives require watch mode, targets are short
SAM-usable noun phrases, durations in range, schedule times parse.
Depends on: domain.rules, domain.enums.
"""

import re

from secondshift.domain.enums import Mode, Primitive
from secondshift.domain.rules import RuleSpec

WATCH_ONLY = {
    Primitive.STATE_FOR_DURATION,
    Primitive.ZONE_EMPTY_FOR_DURATION,
    Primitive.EVENT_BY_DEADLINE,
}
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def validate_spec(spec: RuleSpec) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []
    if len(spec.conditions) > 2:
        errors.append("A rule may have at most 2 conditions.")
    for condition in spec.conditions:
        if condition.primitive in WATCH_ONLY and spec.mode not in (Mode.WATCH, "either"):
            errors.append(f"{condition.primitive.value} needs Watch mode.")
        if condition.target and len(condition.target.split()) > 5:
            errors.append(f"Target '{condition.target}' is too long for a SAM prompt (<= 5 words).")
        if condition.duration_min is not None and not (0.5 <= condition.duration_min <= 240):
            errors.append("Durations must be between 0.5 and 240 minutes.")
        if condition.deadline_local and not _TIME.match(condition.deadline_local):
            errors.append(f"Deadline '{condition.deadline_local}' is not HH:MM.")
    if spec.schedule:
        for value in (spec.schedule.start_local, spec.schedule.end_local):
            if value and not _TIME.match(value):
                errors.append(f"Schedule time '{value}' is not HH:MM.")
    return errors
