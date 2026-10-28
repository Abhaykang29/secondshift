"""Meta text/vision adapter (Muse Spark 1.3 / Muse Wonder).

Phase 7 only. TODO(API): base URL, image part format, structured output.
Depends on: providers.base, providers.cost.
"""

from typing import Literal, NoReturn, TypeVar

from pydantic import BaseModel

from secondshift.providers.base import (
    ImageRef,
    JudgeRequest,
    JudgeResponse,
    ProposeRequest,
    ProposeResponse,
)
from secondshift.providers.cost import ProviderUnavailable

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class MetaVisionReasoner:
    """Real Muse Spark/Wonder client - not yet wired (Phase 7)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def _require(self) -> NoReturn:
        raise ProviderUnavailable("TODO(API): Meta vision adapter lands in Phase 7.")

    def propose_hazards(self, req: ProposeRequest) -> ProposeResponse:
        """TODO(API) Phase 7."""
        self._require()
        raise AssertionError("unreachable")

    def judge(self, req: JudgeRequest) -> JudgeResponse:
        """TODO(API) Phase 7."""
        self._require()
        raise AssertionError("unreachable")

    def complete_json(
        self,
        prompt: str,
        images: list[ImageRef],
        schema: type[SchemaT],
        model_role: Literal["fast", "deep"],
    ) -> SchemaT:
        """TODO(API) Phase 7."""
        self._require()
        raise AssertionError("unreachable")
