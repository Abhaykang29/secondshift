"""Scan orchestration (spec section 9): propose -> verify -> routine -> rank.

Assembles the Report. Fix plans and visualizations are Phase 3 steps that
plug into the same step list; in Phase 2 the report carries hazards,
routine insights and cannot-assess entries.
Depends on: pipeline/*, providers.registry, checklists.loader, domain.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from secondshift.checklists.loader import Pack
from secondshift.domain.checkup import Checkup, Keyframe, Measurement, NarrationFact
from secondshift.domain.enums import Verification
from secondshift.domain.hazards import CannotAssess, Hazard, Report, RoutineInsight
from secondshift.jobs.runner import Job, run_job
from secondshift.pipeline import propose as propose_mod
from secondshift.pipeline import rank as rank_mod
from secondshift.pipeline import routine as routine_mod
from secondshift.pipeline import verify as verify_mod
from secondshift.providers.mock.scenario import load_scenario
from secondshift.providers.registry import Providers
from secondshift.storage.repository import Repository

DISCLAIMER = (
    "SecondShift is a screening tool, not a medical device or an emergency alarm. "
    "It can miss things. For a full assessment, ask an occupational therapist or a "
    "certified professional."
)


@dataclass
class ScanInput:
    """Everything one scan needs, gathered by the API layer."""

    checkup: Checkup
    packs: list[Pack]
    keyframes: list[Keyframe]
    measurements: list[Measurement] = field(default_factory=list)
    narration_facts: list[NarrationFact] = field(default_factory=list)
    scenario_name: str | None = None  # mock providers only
    verify_mode: str = "sam_plus_judge"
    propose_model: str = "spark"  # recorded in stats; model choice is config


@dataclass
class ScanOutput:
    """The scan's products before report assembly."""

    hazards: list[Hazard]
    cannot_assess: list[CannotAssess]
    routine_insights: list[RoutineInsight]
    fix_first: list[str]
    rooms_seen: list[str]


def _set_scenario(providers: Providers, scenario_name: str | None) -> None:
    if scenario_name is None:
        return
    for provider in (providers.vision, providers.segmenter, providers.transcriber):
        if hasattr(provider, "scenario_name"):
            setattr(provider, "scenario_name", scenario_name)


def run_scan(providers: Providers, scan_input: ScanInput) -> ScanOutput:
    """Run propose/verify/routine/rank and return the scan output."""
    _set_scenario(providers, scan_input.scenario_name)
    proposals, cannot, rooms_seen = propose_mod.propose_hazards(
        providers.vision,
        scan_input.packs,
        scan_input.keyframes,
        scan_input.narration_facts,
        scan_input.measurements,
    )
    hazards, verify_cannot = verify_mod.verify_proposals(
        providers.segmenter,
        providers.vision,
        scan_input.packs,
        proposals,
        scan_input.keyframes,
        scan_input.measurements,
        scan_input.checkup.id,
        verify_mode=scan_input.verify_mode,
    )
    cannot = cannot + verify_cannot
    insights: list[RoutineInsight] = []
    # Routine step: computed contacts come from the routine analysis; on
    # mocks they are the scenario's labelled contacts (the geometry that
    # produces them from masks is routine.py, unit-tested separately).
    contacts: list[dict[str, Any]] = []
    path_obstacle_items: list[str] = []
    if scan_input.scenario_name:
        scenario = load_scenario(scan_input.scenario_name)
        contacts = list(scenario.get("routine", {}).get("support_contacts", []))
        path_obstacle_items = list(scenario.get("routine", {}).get("path_obstacles", []))
    if contacts:
        insights.extend(routine_mod.summarize_contacts(scan_input.checkup.id, contacts))
        support_ids = [h.id for h in hazards if h.item_id == "FALL-FURNITURE-SUPPORT"]
        for insight in insights:
            insight.related_hazard_ids = support_ids
        for hazard in hazards:
            if hazard.item_id == "FALL-FURNITURE-SUPPORT":
                hazard.verification = Verification.CONFIRMED
                hazard.verification_reason = (
                    "Routine clip: support contacts counted by the routine analysis."
                )
    for hazard in hazards:
        if hazard.item_id in path_obstacle_items:
            hazard.on_routine_path = True
            insights.append(
                RoutineInsight(
                    id=f"ri-path-{hazard.item_id.lower()}",
                    checkup_id=scan_input.checkup.id,
                    kind="path_obstacle",
                    summary=f"The {hazard.title.lower()} is on the person's walking path.",
                    related_hazard_ids=[hazard.id],
                    evidence=hazard.evidence,
                )
            )
    hazards = rank_mod.dedupe_hazards(hazards)
    confidences = {p.item_id: p.confidence for p in proposals}
    hazards, fix_first = rank_mod.rank_hazards(
        hazards,
        scan_input.packs,
        confidences,
        scan_input.narration_facts,
    )
    return ScanOutput(
        hazards=hazards,
        cannot_assess=cannot,
        routine_insights=insights,
        fix_first=fix_first,
        rooms_seen=rooms_seen,
    )


def assemble_report(checkup: Checkup, output: ScanOutput, stats: dict[str, float]) -> Report:
    """Assemble the Report model from a scan output (fixes land in Phase 3)."""
    confirmed = [h for h in output.hazards if h.verification is Verification.CONFIRMED]
    label = checkup.resident_label or "This home"
    summary = (
        f"{label}: {len(confirmed)} confirmed hazards to fix, "
        f"{len(output.cannot_assess)} things we couldn't check. "
        "Start with the highest-ranked items below."
    )
    return Report(
        checkup_id=checkup.id,
        generated_at=datetime.now(UTC),
        pack_ids=checkup.pack_ids,
        summary=summary,
        fix_first=output.fix_first,
        hazards=output.hazards,
        fixes=[],
        visualizations=[],
        routine_insights=output.routine_insights,
        cannot_assess=output.cannot_assess,
        stats=stats,
        disclaimer=DISCLAIMER,
    )


def run_scan_job(
    store: Repository,
    providers: Providers,
    scan_input: ScanInput,
    data_dir: str = "data",
) -> tuple[Job, Report]:
    """Run a scan as a persisted, resumable job and store its report."""
    job = Job(
        id=uuid.uuid4().hex,
        kind="scan",
        steps=["scan", "fixes", "visualize", "assemble"],
    )
    holder: dict[str, Any] = {}

    def _scan() -> None:
        holder["output"] = run_scan(providers, scan_input)

    def _fixes() -> None:
        from secondshift.pipeline import fixes as fixes_mod

        holder["fix_cards"] = fixes_mod.build_fix_cards(holder["output"].hazards, scan_input.packs)

    def _visualize() -> None:
        from pathlib import Path as _Path

        from secondshift.pipeline import visualize as viz_mod

        viz_dir = _Path(data_dir) / scan_input.checkup.id / "viz"
        visualizations, _befores = viz_mod.render_visualizations(
            holder["output"].hazards, holder.get("fix_cards", []), str(viz_dir)
        )
        holder["visualizations"] = visualizations

    def _assemble() -> None:
        output: ScanOutput = holder["output"]
        stats = {
            "hazards": float(len(output.hazards)),
            "confirmed": float(
                sum(1 for h in output.hazards if h.verification is Verification.CONFIRMED)
            ),
            "cost_usd": providers.cost.spent_usd,
        }
        report = assemble_report(scan_input.checkup, output, stats)
        report.fixes = holder.get("fix_cards", [])
        report.visualizations = holder.get("visualizations", [])
        holder["report"] = report
        store.put("report", scan_input.checkup.id, holder["report"].model_dump(mode="json"))

    run_job(
        store,
        job,
        {
            "scan": _scan,
            "fixes": _fixes,
            "visualize": _visualize,
            "assemble": _assemble,
        },
    )
    if job.status != "done":
        raise RuntimeError(job.error or "scan failed")
    return job, holder["report"]
