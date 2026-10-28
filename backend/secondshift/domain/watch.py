"""Watch mode domain models: sources and events.

Why: Watch is opt-in, single-spot monitoring. These models carry the ROI
and privacy decisions (room type, consent) alongside the source, so no
code path can start watching without them being explicit.
Depends on: domain.enums.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from secondshift.domain.enums import Outcome, RuleState


class WatchSource(BaseModel):
    """One camera source: an old phone, an RTSP camera, or a demo file."""

    id: str
    kind: Literal["phone", "rtsp", "file"]
    label: str
    rtsp_url: str | None = None  # never logged; see docs/PRIVACY.md
    roi: tuple[float, float, float, float] | None = None
    room_type: str | None = None
    privacy_ok: bool = False
    resident_consent: bool = False


class WatchEvent(BaseModel):
    """One state transition of one rule on one source."""

    id: str
    source_id: str
    rule_id: str
    at: datetime
    state_from: RuleState
    state_to: RuleState
    outcome: Outcome
    reason: str
    thumbnail_path: str | None = None
