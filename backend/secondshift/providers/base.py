"""Provider interfaces (Protocols) for SecondShift.

Why: the whole app is built against these interfaces with a deterministic
Mock provider. Real Meta wiring (Phase 7) lives only in providers/meta/
and must satisfy these same Protocols - nothing else changes.
Depends on: domain models.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

from secondshift.domain.checkup import Keyframe, NarrationSegment
from secondshift.domain.hazards import (
    CannotAssess,
    HazardProposal,
    Mask,
)
from secondshift.domain.rules import RuleSpec

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass
class ImageRef:
    """A reference to an image: a path today, bytes/URL adapters later."""

    path: str
    keyframe_id: str | None = None
    t: float | None = None


@dataclass
class ProposeRequest:
    """Input to VisionReasoner.propose_hazards (spec section 9.4)."""

    pack_items_yaml: str
    keyframes: list[Keyframe]
    narration_facts: list[str] = field(default_factory=list)
    measurements: list[str] = field(default_factory=list)
    previous_findings_summary: str = ""
    model_role: Literal["fast", "deep"] = "fast"


@dataclass
class ProposeResponse:
    """Structured output of a propose pass."""

    proposals: list[HazardProposal]
    cannot_assess: list[CannotAssess] = field(default_factory=list)
    rooms_seen: list[str] = field(default_factory=list)
    # One room label per keyframe in the request, aligned by image
    # order. Empty when the provider gives no per-frame labels.
    keyframe_rooms: list[str] = field(default_factory=list)


@dataclass
class JudgeRequest:
    """Input to VisionReasoner.judge (verification / state / re-check)."""

    claim: str
    images: list[ImageRef]
    context: str = ""
    model_role: Literal["fast", "deep"] = "fast"


@dataclass
class JudgeResponse:
    """A judge verdict: one of the Verification string values, plus a reason."""

    verification: str
    reason: str


class VisionReasoner(Protocol):
    """Text/vision reasoning: propose, judge, and generic structured JSON."""

    def propose_hazards(self, req: ProposeRequest) -> ProposeResponse:
        """Propose hazards from keyframes against the loaded packs."""
        ...

    def judge(self, req: JudgeRequest) -> JudgeResponse:
        """Judge one claim against its evidence crops."""
        ...

    def compile_rule(self, text: str, mode_hint: str, precheck_flags: list[str]) -> RuleSpec:
        """Compile a plain-English rule (Layer 2 of rules/compiler.py)."""
        ...

    def complete_json(
        self,
        prompt: str,
        images: list[ImageRef],
        schema: type[SchemaT],
        model_role: Literal["fast", "deep"],
    ) -> SchemaT:
        """Run a prompt and validate the reply against a Pydantic schema."""
        ...

    def plan_fix(
        self,
        hazard_title: str,
        description: str,
        fixes: list[dict[str, str]],
        language: str,
    ) -> dict[str, object] | None:
        """Pick a fix from the library (pass 2 E.6). None = no opinion."""
        ...

    def summarize_report(self, report_json: str, language: str) -> str | None:
        """Write the report summary (pass 2 E.7). None = deterministic."""
        ...

    def judge_recheck(
        self, hazard_title: str, before: ImageRef | None, after: ImageRef | None
    ) -> dict[str, object] | None:
        """Judge a contested re-check item (pass 2 E.8). None = no opinion."""
        ...

    def routine_insights(self, computed_numbers: str) -> list[dict[str, object]] | None:
        """Write routine insight summaries from geometry (pass 2 E.5)."""
        ...

    def classify_room(self, image: ImageRef) -> dict[str, object] | None:
        """Classify a room for the Watch guard (pass 2 G.3)."""
        ...

    def judge_state(self, target: str, question: str, image: ImageRef) -> str | None:
        """Judge an object's visible state in one frame (pass 2 G.2)."""
        ...


class Segmenter(Protocol):
    """Text-prompted segmentation (SAM). The verifier, not decoration."""

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        """Segment one image for each noun-phrase prompt."""
        ...

    def segment_video(self, frames: list[ImageRef], prompts: list[str]) -> dict[str, list[Mask]]:
        """Segment frames; may fall back to per-frame segment calls."""
        ...


class ImageEditor(Protocol):
    """Masked image edits for 'after' visualizations (Muse Image)."""

    def edit(self, image: ImageRef, mask_png: bytes, prompt: str) -> bytes:
        """Return edited image bytes for the masked region only."""
        ...


class Transcriber(Protocol):
    """Speech-to-text (Muse Voice Transcribe). Speech-to-text only."""

    def transcribe(self, audio_path: str, language_hint: str | None) -> list[NarrationSegment]:
        """Transcribe an audio file into timestamped segments."""
        ...
