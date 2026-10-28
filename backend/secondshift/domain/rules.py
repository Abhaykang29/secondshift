"""Rule domain models: schedules, conditions, compiled specs, outcomes.

Why: a family's plain-English sentence becomes a RuleSpec - a small,
verifiable program - or it is refused with observable alternatives.
This module is that contract, shared by the compiler, evaluators and Watch.
Depends on: domain.enums, domain.hazards (Evidence).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from secondshift.domain.enums import CompileStatus, Mode, Outcome, Primitive
from secondshift.domain.hazards import Evidence


def _all_days() -> list[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]]:
    """All seven days - the default rule schedule."""
    return ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _default_notify() -> list[Literal["app", "hub_voice", "whatsapp_share"]]:
    """Default notification channels for a rule: in-app only."""
    return ["app"]


class Schedule(BaseModel):
    """Days and local time window a rule is active in (may wrap midnight)."""

    days: list[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]] = Field(
        default_factory=_all_days
    )
    start_local: str | None = None
    end_local: str | None = None


class Condition(BaseModel):
    """One checkable condition, built from exactly one Primitive."""

    primitive: Primitive
    target: str | None = None
    target_state: str | None = None
    anchor: str | None = None
    area_hint: str | None = None
    duration_min: float | None = None
    deadline_local: str | None = None


class RuleSpec(BaseModel):
    """A compiled (or refused / needs-clarification) rule."""

    id: str
    original_text: str
    status: CompileStatus
    mode: Mode | Literal["either"]
    conditions: list[Condition]
    schedule: Schedule | None = None
    evidence_policy: dict[str, float | int] = Field(
        default_factory=lambda: {"min_confirmations": 2, "min_mask_score": 0.5}
    )
    notify: list[Literal["app", "hub_voice", "whatsapp_share"]] = Field(
        default_factory=_default_notify
    )
    human_summary: str
    clarifying_question: str | None = None
    refusal_reason: str | None = None
    alternatives: list[str] = Field(default_factory=list)
    compiler_version: str = "0.1.0"


class RuleOutcome(BaseModel):
    """The three-state evaluation of a rule at a moment in time."""

    rule_id: str
    outcome: Outcome
    reason: str
    evidence: Evidence | None = None
    evaluated_at: datetime
