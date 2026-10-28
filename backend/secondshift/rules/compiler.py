"""Rule compiler (spec section 9.12).

Two layers: the deterministic observability precheck runs first and can
force a refusal; then compilation. On the real path Layer 2 is Spark with
prompts/rule_compiler.md; here is the deterministic mock compiler, which
covers the Appendix B sentences with explicit patterns plus generic
duration/state fallbacks. If the precheck flagged and compilation would
succeed anyway, the refusal wins and the conflict is logged in the spec's
refusal_reason.
Depends on: rules.observability, rules.validate, domain.rules.
"""

import re
import uuid

from secondshift.domain.enums import CompileStatus, Mode, Primitive
from secondshift.domain.rules import Condition, RuleSpec, Schedule
from secondshift.rules.observability import REFUSAL_FLAGS, precheck
from secondshift.rules.validate import validate_spec

COMPILER_VERSION = "0.4.0-mock"

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

_CLARIFICATIONS: list[tuple[str, str]] = [
    (
        r"bookcase is still strapped",
        "Anti-tip straps are usually hidden behind the bookcase, so a camera often can't tell. Can you check behind it once, and shall I watch for the bookcase moving instead?",
    ),
    (r"fridge door is left open", "For how long before I alert you?"),
    (r"^tell me if the gate is open\.?$", "Which gate - and for how long before I alert you?"),
    (
        r"pills aren't taken|pills are not taken",
        "Which pill box, and what time window should I check?",
    ),
    (
        r"door opens at night",
        "Which door, and what hours count as night? (A $15 door sensor is more reliable for this than a camera.)",
    ),
    (r"^watch the stove\.?$", "What about the stove - on with nobody there, or something else?"),
]


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
        compiler_version=COMPILER_VERSION,
    )


def _compiled(
    text: str,
    mode_hint: str,
    conditions: list[Condition],
    summary: str,
    schedule: Schedule | None = None,
) -> RuleSpec:
    spec = _spec(
        text,
        mode_hint,
        CompileStatus.COMPILED,
        conditions=conditions,
        human_summary=summary,
        schedule=schedule,
    )
    errors = validate_spec(spec)
    if errors:
        return _spec(
            text,
            mode_hint,
            CompileStatus.NEEDS_CLARIFICATION,
            human_summary=summary,
            clarifying_question="That rule needs a fix: " + "; ".join(errors),
        )
    return spec


def compile_rule(text: str, mode_hint: str = "checkup") -> RuleSpec:
    """Compile one plain-English sentence into a RuleSpec (mock Layer 2)."""
    lowered = text.lower().strip()
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
    for pattern, question in _CLARIFICATIONS:
        if re.search(pattern, lowered):
            return _spec(
                text,
                mode_hint,
                CompileStatus.NEEDS_CLARIFICATION,
                human_summary=f"Almost checkable: {text}",
                clarifying_question=question,
            )

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
