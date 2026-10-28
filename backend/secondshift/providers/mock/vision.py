"""Mock VisionReasoner - scenario-driven (spec section 11.2).

Proposals come from the active scenario YAML, filtered to the pack items
in the request, so the whole app works end to end with any uploaded video.
The judge is deterministic: a presence claim SAM could not find any mask
for is rejected; anything else uncertain goes to a human, never a guess.
Depends on: providers.base, providers.mock.scenario.
"""

from typing import Literal, TypeVar

from pydantic import BaseModel

from secondshift.domain.hazards import HazardProposal
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

    def complete_json(
        self,
        prompt: str,
        images: list[ImageRef],
        schema: type[SchemaT],
        model_role: Literal["fast", "deep"],
    ) -> SchemaT:
        """Not used by mock-path code (mock callers use deterministic code)."""
        raise NotImplementedError("Mock complete_json is not used on mock paths.")
