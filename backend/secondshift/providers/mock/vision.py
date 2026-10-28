"""Mock VisionReasoner.

Why: the entire app must work end to end with no API keys. The mock is
deterministic and scenario-driven; in Phase 0 it returns an empty propose
response and a needs_human judge verdict - Phase 2 wires scenario files.
Depends on: providers.base.
"""

from typing import Literal, TypeVar

from pydantic import BaseModel

from secondshift.providers.base import (
    ImageRef,
    JudgeRequest,
    JudgeResponse,
    ProposeRequest,
    ProposeResponse,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class MockVisionReasoner:
    """Deterministic stand-in for Muse Spark / Wonder."""

    def propose_hazards(self, req: ProposeRequest) -> ProposeResponse:
        """Return no proposals in Phase 0 (scenarios land in Phase 2)."""
        return ProposeResponse(proposals=[], rooms_seen=[])

    def judge(self, req: JudgeRequest) -> JudgeResponse:
        """Conservative default: ask a human rather than guess."""
        return JudgeResponse(verification="needs_human", reason="Mock judge: human review.")

    def complete_json(
        self,
        prompt: str,
        images: list[ImageRef],
        schema: type[SchemaT],
        model_role: Literal["fast", "deep"],
    ) -> SchemaT:
        """Phase 0: not implemented for arbitrary schemas."""
        raise NotImplementedError("Mock complete_json lands with its first caller.")
