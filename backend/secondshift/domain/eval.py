"""Evaluation domain models: ground truth and run summaries.

Why: eval is how we prove the system works (spec section 15). Ground truth
is labelled by humans against checklist items; summaries are what the
/eval page and demo show.
Depends on: nothing beyond pydantic.
"""

from pydantic import BaseModel, Field


class GroundTruthHazard(BaseModel):
    """One human-labelled hazard in an eval capture."""

    item_id: str
    room: str
    time_ranges: list[tuple[float, float]]
    note: str | None = None


class EvalCapture(BaseModel):
    """One labelled video in an eval dataset manifest."""

    capture_id: str
    video_path: str
    pack_ids: list[str]
    hazards: list[GroundTruthHazard]
    unassessable: list[str] = Field(default_factory=list)


class EvalRunSummary(BaseModel):
    """Headline metrics for one eval run / ablation config."""

    config_name: str
    precision: float
    recall: float
    f1: float
    confirmed_precision: float
    needs_human_rate: float
    cannot_assess_rate: float
    cost_usd_per_scan: float
    latency_s_per_scan: float
    per_item: dict[str, dict[str, float]]
