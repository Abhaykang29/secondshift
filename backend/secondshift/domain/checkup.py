"""Check-up domain models: consent, checkups, captures, keyframes.

Why: a Checkup is the unit a family creates; Captures are its videos;
Keyframes are the stills the pipeline actually reasons about. These models
are the contract between capture, pipeline, API and frontend.
Depends on: domain.enums.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from secondshift.domain.enums import CaptureKind


class Consent(BaseModel):
    """Consent captured before any filming (spec section 14).

    resident_informed exists because the person who lives in the home, not
    just the person holding the phone, must agree to be screened.
    """

    resident_informed: bool
    no_private_moments: bool
    retention_days: int = 30
    keep_raw_video: bool = False


class Checkup(BaseModel):
    """One home check-up, against one or more checklist packs."""

    id: str
    created_at: datetime
    pack_ids: list[str]
    resident_label: str | None = None
    language: str = "en"
    consent: Consent


class Capture(BaseModel):
    """One uploaded/recorded video belonging to a checkup."""

    id: str
    checkup_id: str
    kind: CaptureKind
    file_path: str | None = None
    duration_s: float
    width: int
    height: int
    fps: float
    source: Literal["phone_upload", "phone_record", "rayban_import", "synthetic"]


class Keyframe(BaseModel):
    """One selected still frame, with quality metrics (spec section 9.1)."""

    id: str
    capture_id: str
    t: float
    image_path: str
    sharpness: float
    brightness: float
    usable: bool
    room_guess: str | None = None


class NarrationSegment(BaseModel):
    """One transcribed narration segment, timestamped to the capture."""

    capture_id: str
    t_start: float
    t_end: float
    text: str
    language: str | None = None


class Measurement(BaseModel):
    """A number the family enters by hand (e.g. toilet seat height)."""

    id: str
    checkup_id: str
    label: str
    value: float
    unit: str
    note: str | None = None


class NarrationFact(BaseModel):
    """A routine fact extracted from narration (spec section 9.3).

    Health details are dropped before a fact is ever stored here.
    """

    fact: str
    t: float
    affects: list[str] = Field(default_factory=list)
