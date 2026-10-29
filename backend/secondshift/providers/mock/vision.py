"""Mock VisionReasoner - scenario-driven (spec section 11.2).

Proposals come from the active scenario YAML, filtered to the pack items
in the request, so the whole app works end to end with any uploaded video.
The judge is deterministic: a presence claim SAM could not find any mask
for is rejected; anything else uncertain goes to a human, never a guess.
Depends on: providers.base, providers.mock.scenario.
"""

import re
from typing import Literal, TypeVar

from pydantic import BaseModel

from secondshift.domain.enums import CompileStatus, Primitive
from secondshift.domain.hazards import HazardProposal
from secondshift.domain.rules import Condition, RuleSpec, Schedule
from secondshift.providers.base import (
    ImageRef,
    JudgeRequest,
    JudgeResponse,
    ProposeRequest,
    ProposeResponse,
)
from secondshift.providers.mock.scenario import default_scenario_name, load_scenario

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class MockVisionReasoner:
    """Deterministic stand-in for Muse Spark / Wonder."""

    def __init__(self, scenario_name: str | None = None) -> None:
        self.scenario_name = scenario_name or default_scenario_name()

    def propose_hazards(self, req: ProposeRequest) -> ProposeResponse:
        """Return the scenario's proposals for items in the loaded packs."""
        scenario = load_scenario(self.scenario_name)
        proposals: list[HazardProposal] = []
        for raw in scenario.get("proposals", []):
            if raw["item_id"] not in req.pack_items_yaml:
                continue
            proposals.append(
                HazardProposal(
                    item_id=raw["item_id"],
                    room=raw["room"],
                    description=raw.get("description", raw["why_risky"]),
                    evidence_timestamps=[float(t) for t in raw["t"]],
                    sam_prompts=list(raw.get("sam_prompts", [])),
                    safety_prompts=list(raw.get("safety_prompts", [])),
                    confidence=float(raw.get("confidence", 0.8)),
                    why_risky=raw["why_risky"],
                    observed_interaction=raw.get("observed_interaction"),
                )
            )
        return ProposeResponse(
            proposals=proposals,
            rooms_seen=list(scenario.get("rooms_seen", [])),
        )

    def judge(self, req: JudgeRequest) -> JudgeResponse:
        """Deterministic judge: no SAM mask for a presence claim -> rejected."""
        if "state_check" in req.context and "sam_found: true" in req.context:
            return JudgeResponse(
                verification="confirmed",
                reason="Mock judge: the visible state matches the claim.",
            )
        if "sam_found: false" in req.context:
            return JudgeResponse(
                verification="rejected",
                reason="SAM found no matching object in the evidence frames.",
            )
        return JudgeResponse(verification="needs_human", reason="Mock judge: human review.")

    # Pass 2 E/G: the mock has no opinions - pipelines use their
    # deterministic paths, and the UI banner says results are mock.
    def plan_fix(self, hazard_title, description, fixes, language):  # type: ignore[no-untyped-def]
        return None

    def summarize_report(self, report_json, language):  # type: ignore[no-untyped-def]
        return None

    def judge_recheck(self, hazard_title, before, after):  # type: ignore[no-untyped-def]
        return None

    def routine_insights(self, computed_numbers):  # type: ignore[no-untyped-def]
        return None

    def classify_room(self, image):  # type: ignore[no-untyped-def]
        return None

    def judge_state(self, target, question, image):  # type: ignore[no-untyped-def]
        return None

    def compile_rule(self, text: str, mode_hint: str, precheck_flags: list[str]) -> RuleSpec:
        """Mock Layer 2: deterministic patterns (tests/dev only)."""
        spec = _deterministic_compile(text, mode_hint)
        spec.compiler_version = "0.4.0-mock"
        return spec

    def complete_json(
        self,
        prompt: str,
        images: list[ImageRef],
        schema: type[SchemaT],
        model_role: Literal["fast", "deep"],
    ) -> SchemaT:
        """Not used by mock-path code (mock callers use deterministic code)."""
        raise NotImplementedError("Mock complete_json is not used on mock paths.")


# --- Deterministic mock Layer 2 (moved from rules/compiler.py, pass 2 D).
# These per-sentence patterns exist ONLY in the mock provider, for unit
# tests and dev mode. The live compiler is Spark (rules/compiler.py).
def _deterministic_compile(text: str, mode_hint: str) -> RuleSpec:
    """The old pattern compiler, kept for mocks; stamps 0.4.0-mock."""
    lowered = text.lower().strip()
    c = Condition
    p = Primitive
    # --- Watch compiled patterns ---
    if "baby gate" in lowered and "open" in lowered and "30 seconds" in lowered:
        return _compiled(
            text,
            mode_hint,
            [
                c(
                    primitive=p.STATE_FOR_DURATION,
                    target="baby gate",
                    target_state="open",
                    duration_min=0.5,
                )
            ],
            "Alert if the baby gate is open for more than 30 seconds",
        )
    if "stove is on" in lowered and "kitchen" in lowered and "10 minutes" in lowered:
        return _compiled(
            text,
            mode_hint,
            [
                c(
                    primitive=p.OBJECT_STATE,
                    target="stove burner",
                    target_state="on (flame or glowing coil)",
                ),
                c(primitive=p.ZONE_EMPTY_FOR_DURATION, duration_min=10.0, area_hint="kitchen"),
            ],
            "Alert if the stove is on and nobody is in the kitchen for 10 minutes",
        )
    if "pill box" in lowered and "opened" in lowered:
        return _compiled(
            text,
            mode_hint,
            [
                c(
                    primitive=p.EVENT_BY_DEADLINE,
                    target="pill box lid",
                    target_state="lid open",
                    deadline_local="21:00",
                )
            ],
            "Alert if the evening pill box isn't opened between 7 and 9 PM",
            schedule=Schedule(start_local="19:00", end_local="21:00"),
        )
    if "front door" in lowered and "open" in lowered and "5 minutes" in lowered:
        return _compiled(
            text,
            mode_hint,
            [
                c(
                    primitive=p.STATE_FOR_DURATION,
                    target="front door",
                    target_state="open",
                    duration_min=5.0,
                )
            ],
            "Alert if the front door is open for more than 5 minutes",
        )
    if "oven door" in lowered and "15 minutes" in lowered:
        return _compiled(
            text,
            mode_hint,
            [
                c(
                    primitive=p.STATE_FOR_DURATION,
                    target="oven door",
                    target_state="open",
                    duration_min=15.0,
                )
            ],
            "Alert if the oven door is open for more than 15 minutes",
        )
    if "cabinet under the sink" in lowered:
        return _compiled(
            text,
            mode_hint,
            [c(primitive=p.OBJECT_STATE, target="cabinet door", target_state="open")],
            "Alert if the cabinet under the sink is open",
        )
    if (
        "camera can't see" in lowered
        or "camera cannot see" in lowered
        or "camera can\u2019t see" in lowered
    ):
        return _compiled(
            text,
            mode_hint,
            [c(primitive=p.CAMERA_HEALTH, area_hint="kitchen")],
            "Alert if the camera can't see the stove",
        )
    # --- Check-up compiled patterns ---
    checkup_patterns: list[tuple[str, Condition, str]] = [
        (
            r"no rug on the stairs",
            c(primitive=p.OBJECT_PRESENT, target="rug", area_hint="stairs"),
            "Check that there is no rug on the stairs",
        ),
        (
            r"night light is still there",
            c(primitive=p.OBJECT_ABSENT, target="night light", anchor="hallway"),
            "Check that the hallway night light is still there",
        ),
        (
            r"nothing is left on the stairs",
            c(primitive=p.OBJECT_PRESENT, target="object on stairs", area_hint="stairs"),
            "Check that nothing is left on the stairs",
        ),
        (
            r"grab bar next to the toilet",
            c(primitive=p.OBJECT_ABSENT, target="grab bar", anchor="toilet"),
            "Check that the grab bar next to the toilet is still installed",
        ),
        (
            r"non-slip mat in the tub",
            c(primitive=p.OBJECT_ABSENT, target="non-slip mat", anchor="bathtub"),
            "Check that there is a non-slip mat in the tub",
        ),
        (
            r"no cords cross the hallway",
            c(primitive=p.OBJECT_PRESENT, target="cord", area_hint="hallway"),
            "Check that no cords cross the hallway",
        ),
        (
            r"cleaning bottles aren't on the low shelf|cleaning bottles are not on the low shelf",
            c(primitive=p.OBJECT_PRESENT, target="cleaning spray bottle", area_hint="kitchen"),
            "Check that the cleaning bottles are not on the low shelf",
        ),
        (
            r"no toys in the crib",
            c(primitive=p.OBJECT_PRESENT, target="stuffed toy in crib", area_hint="nursery"),
            "Check that there are no toys in the crib",
        ),
        (
            r"baby gate at the top of the stairs is still there",
            c(primitive=p.OBJECT_ABSENT, target="baby gate", anchor="staircase"),
            "Check that the baby gate at the top of the stairs is still there",
        ),
    ]
    for pattern, condition, summary in checkup_patterns:
        if re.search(pattern, lowered):
            return _compiled(text, mode_hint, [condition], summary)
    # --- Generic watch fallback: "left open for more than N minutes/seconds" ---
    m = re.search(
        r"if the (.+?) is (?:left )?open for more than (\d+)\s*(minutes|seconds)", lowered
    )
    if m:
        target = m.group(1).strip()
        minutes = float(m.group(2)) / (60.0 if m.group(3) == "seconds" else 1.0)
        return _compiled(
            text,
            mode_hint,
            [
                c(
                    primitive=p.STATE_FOR_DURATION,
                    target=target,
                    target_state="open",
                    duration_min=minutes,
                )
            ],
            f"Alert if the {target} is open for more than {m.group(2)} {m.group(3)}",
        )
    return _spec(
        text,
        mode_hint,
        CompileStatus.NEEDS_CLARIFICATION,
        human_summary=f"Almost checkable: {text}",
        clarifying_question="What exactly should I check - which object, in which room, and in what state?",
    )


from secondshift.rules.compiler import _compiled, _spec  # noqa: E402
