"""Domain package: the shared contract for SecondShift.

Re-exports the public model surface so callers can use
``from secondshift.domain import Hazard`` style imports where convenient,
while the canonical definitions stay in their per-area modules.
"""

from secondshift.domain.checkup import (
    Capture,
    Checkup,
    Consent,
    Keyframe,
    Measurement,
    NarrationFact,
    NarrationSegment,
)
from secondshift.domain.enums import (
    CacheMode,
    CaptureKind,
    CompileStatus,
    ItemKind,
    Mode,
    Outcome,
    Primitive,
    ProviderName,
    RecheckStatus,
    RuleState,
    Severity,
    Verification,
)
from secondshift.domain.eval import EvalCapture, EvalRunSummary, GroundTruthHazard
from secondshift.domain.hazards import (
    CannotAssess,
    Evidence,
    FixCard,
    FixOption,
    Hazard,
    HazardProposal,
    Mask,
    Recheck,
    RecheckItem,
    Report,
    RoutineInsight,
    Visualization,
)
from secondshift.domain.rules import Condition, RuleOutcome, RuleSpec, Schedule
from secondshift.domain.watch import WatchEvent, WatchSource

__all__ = [
    "CacheMode",
    "CannotAssess",
    "Capture",
    "CaptureKind",
    "Checkup",
    "CompileStatus",
    "Condition",
    "Consent",
    "EvalCapture",
    "EvalRunSummary",
    "Evidence",
    "FixCard",
    "FixOption",
    "GroundTruthHazard",
    "Hazard",
    "HazardProposal",
    "ItemKind",
    "Keyframe",
    "Mask",
    "Measurement",
    "Mode",
    "NarrationFact",
    "NarrationSegment",
    "Outcome",
    "Primitive",
    "ProviderName",
    "Recheck",
    "RecheckItem",
    "RecheckStatus",
    "Report",
    "RoutineInsight",
    "RuleOutcome",
    "RuleSpec",
    "RuleState",
    "Schedule",
    "Severity",
    "Verification",
    "Visualization",
    "WatchEvent",
    "WatchSource",
]
