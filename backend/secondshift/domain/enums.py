"""Enumerations for SecondShift.

Why this module exists: every other module (backend pipeline, API, frontend
types, eval) must agree on the exact string values for modes, outcomes and
states. Keeping them here, as the single contract, prevents drift.
Depends on: nothing (stdlib only).
"""

from enum import IntEnum, StrEnum


class Mode(StrEnum):
    """Top-level product mode."""

    CHECKUP = "checkup"
    WATCH = "watch"


class CaptureKind(StrEnum):
    """What kind of video a Capture holds."""

    WALKTHROUGH = "walkthrough"
    ROUTINE = "routine"
    RECHECK = "recheck"


class ItemKind(StrEnum):
    """How a checklist item is verified (see spec section 4)."""

    PRESENCE = "presence"
    ABSENCE = "absence"
    INTERACTION = "interaction"
    MEASUREMENT = "measurement"


class Severity(IntEnum):
    """Pack-assigned severity; feeds the risk score in pipeline/rank.py."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Verification(StrEnum):
    """Result of the propose -> SAM verify step for one hazard."""

    CONFIRMED = "confirmed"
    NEEDS_HUMAN = "needs_human"
    REJECTED = "rejected"
    CANNOT_ASSESS = "cannot_assess"


class RecheckStatus(StrEnum):
    """How a previous hazard changed on a re-check."""

    RESOLVED = "resolved"
    STILL_PRESENT = "still_present"
    NEW = "new"
    CANNOT_TELL = "cannot_tell"


class Outcome(StrEnum):
    """Three-state answer for every rule. We never pretend to know."""

    MET = "met"
    NOT_MET = "not_met"
    CANNOT_TELL = "cannot_tell"


class CompileStatus(StrEnum):
    """Result of compiling a plain-English rule."""

    COMPILED = "compiled"
    REFUSED = "refused"
    NEEDS_CLARIFICATION = "needs_clarification"


class Primitive(StrEnum):
    """The small set of checkable rule primitives (spec section 8)."""

    OBJECT_PRESENT = "object_present"
    OBJECT_ABSENT = "object_absent"
    OBJECT_STATE = "object_state"
    STATE_FOR_DURATION = "state_for_duration"
    ZONE_EMPTY_FOR_DURATION = "zone_empty_for_duration"
    EVENT_BY_DEADLINE = "event_by_deadline"
    CAMERA_HEALTH = "camera_health"


class RuleState(StrEnum):
    """Live state of a Watch rule."""

    IDLE = "idle"
    WATCHING = "watching"
    PENDING = "pending"
    ALERT = "alert"
    CANNOT_SEE = "cannot_see"


class ProviderName(StrEnum):
    """Which provider implementation the registry should build."""

    MOCK = "mock"
    META = "meta"
    LOCAL = "local"


class CacheMode(StrEnum):
    """Record/replay behaviour for provider calls (spec section 11.3)."""

    OFF = "off"
    RECORD = "record"
    REPLAY = "replay"
    AUTO = "auto"
