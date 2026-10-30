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
    # Two-way check (2026-10-30): the SAM sweep runs on the live path
    # (scenario is None); scripted demo scenarios define their own
    # world and skip it.
    sweep: bool = False
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


def attach_cross_pack_tags(hazards: list[Hazard], packs: list[Pack]) -> list[Hazard]:
    """Pass 3 P1.3: one physical object can satisfy items in several
    packs (a floor cord is both FALL-FLOOR-CORD and PET-CORDS-
    CHEWABLE). Items sharing a dedupe_key are the same object class:
    a confirmed (or needs-human) hazard earns the pack tag of every
    selected pack that carries an item with the same dedupe_key, even
    when that pack's own item was never separately proposed - one
    hazard card, several pack chips."""
    key_by_item: dict[str, str | None] = {}
    packs_by_key: dict[str, set[str]] = {}
    for pack in packs:
        for item in pack.items:
            key_by_item[item.id] = item.dedupe_key
            if item.dedupe_key:
                packs_by_key.setdefault(item.dedupe_key, set()).add(pack.pack_id)
    for hazard in hazards:
        if hazard.verification not in (Verification.CONFIRMED, Verification.NEEDS_HUMAN):
            continue
        key = key_by_item.get(hazard.item_id)
        if not key:
            continue
        for pack_id in sorted(packs_by_key.get(key, set())):
            if pack_id not in hazard.pack_tags:
                hazard.pack_tags.append(pack_id)
    return hazards


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
    if scan_input.sweep and scan_input.verify_mode != "none":
        from secondshift.pipeline import sweep as sweep_mod

        covered = {
            (h.item_id, h.room)
            for h in hazards
            if h.verification in (Verification.CONFIRMED, Verification.NEEDS_HUMAN)
        }
        swept = sweep_mod.sweep_presence(
            providers.segmenter,
            providers.vision,
            scan_input.packs,
            scan_input.keyframes,
            rooms_seen,
            covered,
            scan_input.checkup.id,
            len(proposals),
            verify_mode=scan_input.verify_mode,
        )
        hazards = sweep_mod.merge_sweep_hazards(hazards, swept)
    hazards = attach_cross_pack_tags(hazards, scan_input.packs)
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
        insights.extend(
            routine_mod.summarize_contacts(scan_input.checkup.id, contacts, vision=providers.vision)
        )
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
    dedupe_keys = {item.id: item.dedupe_key for pack in scan_input.packs for item in pack.items}
    hazards = rank_mod.dedupe_hazards(hazards, dedupe_keys)
    confidences = {p.item_id: p.confidence for p in proposals}
    hazards, fix_first = rank_mod.rank_hazards(
        hazards,
        scan_input.packs,
        confidences,
        scan_input.narration_facts,
    )
    # Smoke-test fix 3: the couldn't-assess list is cleaned against the
    # FINAL verdicts and the rooms actually seen - deduped, no items
    # that got a verdict, no rooms that were filmed.
    cannot = propose_mod.clean_cannot_assess(cannot, hazards, rooms_seen)
    # Pass 3 P2: items no camera can settle always appear as
    # cannot-assess with their exact wording, proposed or not; a
    # hazard verdict for one is a pipeline bug, so drop it here.
    hazards = [
        h
        for h in hazards
        if not any(
            item.id == h.item_id and item.always_cannot_assess
            for pack in scan_input.packs
            for item in pack.items
        )
    ]
    verdict_items = {h.item_id for h in hazards}
    for pack in scan_input.packs:
        for item in pack.items:
            if not item.always_cannot_assess or item.id in verdict_items:
                continue
            # The exact wording wins over any generic propose entry.
            for entry in cannot:
                if entry.area == item.id:
                    entry.reason = "not_visible_by_design"
                    entry.detail = item.always_cannot_assess
                    break
            else:
                cannot.append(
                    CannotAssess(
                        area=item.id,
                        reason="not_visible_by_design",
                        detail=item.always_cannot_assess,
                    )
                )
    return ScanOutput(
        hazards=hazards,
        cannot_assess=cannot,
        routine_insights=insights,
        fix_first=fix_first,
        rooms_seen=rooms_seen,
    )


def assemble_report(
    checkup: Checkup,
    output: ScanOutput,
    stats: dict[str, float],
    vision: object | None = None,
) -> Report:
    """Assemble the Report from a scan output.

    Pass 2 E.7: with a live vision provider, Spark writes the summary
    via prompts/report_summary.md from the report's own facts; the
    deterministic summary remains the fallback (and the mock path).
    """
    confirmed = [h for h in output.hazards if h.verification is Verification.CONFIRMED]
    label = checkup.resident_label or "This home"
    summary = (
        f"{label}: {len(confirmed)} confirmed hazards to fix, "
        f"{len(output.cannot_assess)} things we couldn't check. "
        "Start with the highest-ranked items below."
    )
    if vision is not None:
        import json as _json

        facts = _json.dumps(
            {
                "home_label": label,
                "confirmed": [
                    {"title": h.title, "room": h.room, "risk": h.risk_score} for h in confirmed
                ],
                "needs_human": [
                    h.title for h in output.hazards if h.verification is Verification.NEEDS_HUMAN
                ],
                "cannot_assess_count": len(output.cannot_assess),
            }
        )
        written = vision.summarize_report(facts, "en")  # type: ignore[attr-defined]
        if written:
            summary = written
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

        holder["fix_cards"] = fixes_mod.build_fix_cards(
            holder["output"].hazards, scan_input.packs, vision=providers.vision
        )

    def _visualize() -> None:
        from pathlib import Path as _Path

        from secondshift.pipeline import visualize as viz_mod

        viz_dir = _Path(data_dir) / scan_input.checkup.id / "viz"
        visualizations, _befores = viz_mod.render_visualizations(
            holder["output"].hazards,
            holder.get("fix_cards", []),
            str(viz_dir),
            keyframes={kf.id: kf.image_path for kf in scan_input.keyframes if kf.image_path},
            image_editor=providers.image_editor,
            segmenter=providers.segmenter,
            vision=providers.vision,
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
        report = assemble_report(scan_input.checkup, output, stats, vision=providers.vision)
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
