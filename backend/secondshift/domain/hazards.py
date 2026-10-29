"""Hazard domain models: proposals, verified hazards, fixes, reports.

Why: HazardProposal is what a vision model *claims*; Hazard is what remains
after SAM verification. Keeping them separate is the core honesty mechanism
of the product - a claim is never shown to a family as a fact.
Depends on: domain.enums, domain.checkup (via ids only).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from secondshift.domain.enums import ItemKind, RecheckStatus, Severity, Verification


class Mask(BaseModel):
    """A segmentation mask on one keyframe, in normalized 0-1 coordinates."""

    keyframe_id: str
    polygon: list[tuple[float, float]] | None = None
    rle: str | None = None
    bbox: tuple[float, float, float, float]
    score: float
    prompt: str


class Evidence(BaseModel):
    """Everything backing a hazard claim: frames, masks, notes, measurements."""

    keyframe_ids: list[str]
    timestamps: list[float]
    masks: list[Mask] = Field(default_factory=list)
    narration_notes: list[str] = Field(default_factory=list)
    measurement_ids: list[str] = Field(default_factory=list)


class HazardProposal(BaseModel):
    """What the vision model claims, before verification (spec section 9.4)."""

    item_id: str
    room: str
    description: str
    evidence_timestamps: list[float]
    sam_prompts: list[str]
    safety_prompts: list[str] = Field(default_factory=list)
    confidence: float
    why_risky: str
    observed_interaction: str | None = None


class Hazard(BaseModel):
    """A hazard after verification, ranked for the report."""

    id: str
    checkup_id: str
    pack_id: str
    pack_tags: list[str] = Field(default_factory=list)
    item_id: str
    kind: ItemKind
    room: str
    title: str
    description: str
    why_it_matters: str
    severity: Severity
    on_routine_path: bool = False
    verification: Verification
    verification_reason: str
    evidence: Evidence
    risk_score: float
    rank: int | None = None


class FixOption(BaseModel):
    """One fix, copied from the pack library. Never invented by a model."""

    id: str
    title: str
    how: str
    difficulty: Literal["easy", "medium", "pro"]
    cost_estimate: str
    visualization_prompt: str | None = None


class FixCard(BaseModel):
    """The fix plan shown to a family for one hazard."""

    id: str
    hazard_id: str
    chosen: FixOption
    alternatives: list[FixOption]
    plain_language_steps: list[str]
    status: Literal["todo", "done", "skipped"] = "todo"
    note: str | None = None


class Visualization(BaseModel):
    """A rendered 'after' picture for a fix. Always watermarked."""

    id: str
    hazard_id: str
    source_keyframe_id: str
    image_path: str
    prompt_used: str
    watermark: str = "Visualization \u2014 not a photo"


class RoutineInsight(BaseModel):
    """An insight from the routine clip, about person-environment interaction."""

    id: str
    checkup_id: str
    kind: Literal[
        "support_contact", "path_obstacle", "low_seat_difficulty", "reaching_high", "dark_path"
    ]
    summary: str
    count: int | None = None
    related_hazard_ids: list[str] = Field(default_factory=list)
    evidence: Evidence


class CannotAssess(BaseModel):
    """An area we honestly could not check. First-class, visible output."""

    area: str
    reason: Literal[
        "not_filmed",
        "too_dark",
        "too_blurry",
        "occluded",
        "needs_measurement",
        "not_visible_by_design",
    ]
    detail: str


class Report(BaseModel):
    """The full check-up report (spec section 9.10)."""

    checkup_id: str
    generated_at: datetime
    pack_ids: list[str]
    summary: str
    fix_first: list[str]
    hazards: list[Hazard]
    fixes: list[FixCard]
    visualizations: list[Visualization]
    routine_insights: list[RoutineInsight]
    cannot_assess: list[CannotAssess]
    stats: dict[str, float]
    disclaimer: str


class RecheckItem(BaseModel):
    """One row of a re-check diff."""

    hazard_id: str | None
    item_id: str
    room: str
    status: RecheckStatus
    reason: str
    before_keyframe_id: str | None
    after_keyframe_id: str | None


class Recheck(BaseModel):
    """A re-check of a checkup against a new capture."""

    id: str
    checkup_id: str
    capture_id: str
    created_at: datetime
    items: list[RecheckItem]
    rule_outcomes: list["RuleOutcome"] = Field(default_factory=list)
    score_before: float
    score_after: float


from secondshift.domain.rules import RuleOutcome  # noqa: E402

Recheck.model_rebuild()
