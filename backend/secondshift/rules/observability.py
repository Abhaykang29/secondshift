"""Observability precheck (spec section 9.12, Layer 1).

Deterministic pattern flags for things a camera cannot see: the future,
intentions, internal states, non-visual properties, identity/tracking,
audio, medical judgement, and Watch in private rooms. A flag forces a
refusal or a clarifying question - the LLM still writes the wording on
the real path; on mocks the compiler uses the same flags.
Depends on: re (stdlib).
"""

import re

_PATTERNS: dict[str, list[str]] = {
    "future_prediction": [
        r"\bwill\b",
        r"going to",
        r"about to",
        r"before\b.*\bfall",
        r"predict",
        r"catch fire",
    ],
    "intention": [r"planning to", r"wants to", r"thinking (of|about)", r"intend", r"planning"],
    "internal_state": [
        r"in pain",
        r"\bdizzy\b",
        r"\bsad\b",
        r"is okay",
        r"is sick",
        r"feelings",
        r"forgets things",
        r"forgetful",
    ],
    "non_visual": [
        r"\bsmell\b",
        r"gas leak",
        r"temperature",
        r"too hot",
        r"is hot",
        r"\bworks\b",
        r"working",
        r"battery",
    ],
    "identity_tracking": [
        r"tell me who",
        r"recogniz",
        r"follow .* around",
        r"where .* (is going|goes)",
        r"track",
        r"anyone strange",
        r"leaves the house",
        r"comes into",
    ],
    "audio": [r"crying", r"shouting", r"alarm sounds", r"\bscreaming\b"],
    "medical": [r"breathing", r"right pills", r"took (his|her|the) pills"],
    "private_room_watch": [r"watch the bathroom", r"in the bathroom", r"shower"],
}

REFUSAL_FLAGS = {
    "future_prediction",
    "intention",
    "internal_state",
    "non_visual",
    "identity_tracking",
    "audio",
    "medical",
    "private_room_watch",
}


def precheck(text: str, mode_hint: str = "checkup") -> list[str]:
    """Return the sorted flag names that fire for a rule sentence."""
    lowered = text.lower()
    flags: list[str] = []
    for name, patterns in _PATTERNS.items():
        if name == "private_room_watch" and mode_hint != "watch":
            continue
        if any(re.search(p, lowered) for p in patterns):
            flags.append(name)
    if re.search(r"house is safe|everything is (fine|ok|safe)", lowered):
        flags.append("too_vague")
    return sorted(flags)
