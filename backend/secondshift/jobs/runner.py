"""Background job runner placeholder.

Phase 2 implements resumable, step-by-step jobs (spec section 9). Phase 0
only fixes the shape: a Job has named steps, each step is idempotent.
Depends on: nothing yet.
"""

from dataclasses import dataclass, field


@dataclass
class Job:
    """One background job: an ordered list of step names and their status."""

    id: str
    kind: str
    steps: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    status: str = "queued"  # queued | running | done | failed
