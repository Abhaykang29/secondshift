"""Rule compiler (spec section 9.12) - pass 2 Phase D.

Layer 1 is the deterministic observability precheck: it runs first and
can force a refusal, and the refusal always wins. Layer 2 is Spark via
prompts/rule_compiler.md through the vision provider. There are NO
per-sentence regex patterns on this path anymore: when no live
compiler is available, compile_rule returns needs_clarification
("I can't compile rules right now") instead of guessing. The old
deterministic patterns survive ONLY inside the mock provider
(providers/mock/vision.py), clearly stamped 0.4.0-mock, for tests and
dev mode.
Depends on: rules.observability, rules.validate, domain.rules,
providers.base (typing only).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from secondshift.domain.enums import CompileStatus, Mode
from secondshift.domain.rules import Condition, RuleSpec, Schedule

if TYPE_CHECKING:
    from secondshift.providers.base import VisionReasoner
from secondshift.rules.observability import REFUSAL_FLAGS, precheck
from secondshift.rules.validate import validate_spec

COMPILER_VERSION = "2.0.0"

_REFUSALS: dict[str, tuple[str, list[str]]] = {
    "future_prediction": (
        "A camera can't predict the future - it can only check what is visible now.",
        [
            "Make sure there's no rug on the stairs",
            "Check that the hallway night light is still there",
            "Make sure nothing is left on the stairs",
        ],
    ),
    "internal_state": (
        "A camera can't see pain, feelings or health - only objects and visible states.",
        [
            "Check that the hallway night light is still there",
            "Tell me if the front door is left open for more than 5 minutes",
        ],
    ),
    "intention": (
        "A camera can't see what someone is planning or thinking.",
        ["Tell me if the front door is left open for more than 5 minutes"],
    ),
    "non_visual": (
        "A camera can't smell, feel temperature, or tell whether a device works. A dedicated sensor is the right tool for that.",
        ["Check that the grab bar next to the toilet is still installed"],
    ),
    "identity_tracking": (
        "We never identify people or track where they go - we only check spaces and objects.",
        [
            "Tell me if the front door is left open for more than 5 minutes",
            "Tell me if the baby gate at the top of the stairs is left open for more than 30 seconds",
        ],
    ),
    "audio": (
        "Watch mode has no audio - it only looks at one spot.",
        ["Tell me if the cabinet under the sink is open"],
    ),
    "medical": (
        "That's a medical judgement a camera must not make. For breathing or medication, use a certified medical device and ask their doctor.",
        ["Let me know if Mom's evening pill box isn't opened between 7 and 9 PM"],
    ),
    "private_room_watch": (
        "Watch mode is never allowed in bathrooms.",
        [
            "Tell me if the baby gate at the top of the stairs is left open for more than 30 seconds",
            "Check that the grab bar next to the toilet is still installed",
        ],
    ),
}


def _spec(
    text: str,
    mode_hint: str,
    status: CompileStatus,
    conditions: list[Condition] | None = None,
    schedule: Schedule | None = None,
    human_summary: str = "",
    clarifying_question: str | None = None,
    refusal_reason: str | None = None,
    alternatives: list[str] | None = None,
    version: str = COMPILER_VERSION,
) -> RuleSpec:
    mode: Mode | str = Mode.WATCH if mode_hint == "watch" else Mode.CHECKUP
    return RuleSpec(
        id=uuid.uuid4().hex,
        original_text=text,
        status=status,
        mode=mode,  # type: ignore[arg-type]
        conditions=conditions or [],
        schedule=schedule,
        human_summary=human_summary,
        clarifying_question=clarifying_question,
        refusal_reason=refusal_reason,
        alternatives=alternatives or [],
        compiler_version=version,
    )


def _compiled(
    text: str,
    mode_hint: str,
    conditions: list[Condition],
    summary: str,
    schedule: Schedule | None = None,
    version: str = COMPILER_VERSION,
) -> RuleSpec:
    spec = _spec(
        text,
        mode_hint,
        CompileStatus.COMPILED,
        conditions=conditions,
        human_summary=summary,
        schedule=schedule,
        version=version,
    )
    errors = validate_spec(spec)
    if errors:
        return _spec(
            text,
            mode_hint,
            CompileStatus.NEEDS_CLARIFICATION,
            human_summary=summary,
            clarifying_question="That rule needs a fix: " + "; ".join(errors),
            version=version,
        )
    return spec


def compile_rule(
    text: str,
    mode_hint: str = "checkup",
    vision: VisionReasoner | None = None,
) -> RuleSpec:
    """Compile one plain-English sentence into a RuleSpec.

    Layer 1 (precheck) first; Layer 2 is the vision provider (Spark on
    the real path, the deterministic patterns only inside the mock
    provider). No provider -> an honest needs_clarification.
    """
    flags = precheck(text, mode_hint)
    refusal_flags = [f for f in flags if f in REFUSAL_FLAGS]
    if refusal_flags:
        reason, alternatives = _REFUSALS[refusal_flags[0]]
        return _spec(
            text,
            mode_hint,
            CompileStatus.REFUSED,
            human_summary=f"I can't check that: {text}",
            refusal_reason=reason,
            alternatives=alternatives,
        )
    if "too_vague" in flags:
        return _spec(
            text,
            mode_hint,
            CompileStatus.NEEDS_CLARIFICATION,
            human_summary="That's too broad for one rule.",
            clarifying_question=(
                "Shall I run a check-up instead? I can check the "
                "falls pack (Parent's home) or the babyproofing pack "
                "(Baby's home) - or name one spot to watch."
            ),
        )
    # Layer 2: the vision provider compiles (Spark on the real path).
    if vision is None:
        return _spec(
            text,
            mode_hint,
            CompileStatus.NEEDS_CLARIFICATION,
            human_summary="I can't compile rules right now.",
            clarifying_question=(
                "I can't compile rules right now - the rule compiler is "
                "unavailable. Please try again in a moment."
            ),
        )
    try:
        spec = vision.compile_rule(text, mode_hint, flags)
    except Exception:
        return _spec(
            text,
            mode_hint,
            CompileStatus.NEEDS_CLARIFICATION,
            human_summary="I can't compile rules right now.",
            clarifying_question=(
                "I can't compile rules right now - the rule compiler is "
                "unavailable. Please try again in a moment."
            ),
        )
    errors = validate_spec(spec)
    if errors and spec.status == CompileStatus.COMPILED:
        return _spec(
            text,
            mode_hint,
            CompileStatus.NEEDS_CLARIFICATION,
            human_summary=spec.human_summary,
            clarifying_question="That rule needs a fix: " + "; ".join(errors),
            version=spec.compiler_version,
        )
    return spec
