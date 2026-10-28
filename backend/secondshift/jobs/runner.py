"""Background job runner (spec section 9 preamble).

Every pipeline step is persisted as it completes, so a re-run skips
finished steps (idempotent, resumable). Phase 2 runs steps synchronously
in-process; the interface is the one a queue worker would use later.
Depends on: storage.repository.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from secondshift.storage.repository import Repository


@dataclass
class Job:
    """One background job: an ordered list of step names and their status."""

    id: str
    kind: str
    steps: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    status: str = "queued"  # queued | running | done | failed
    error: str | None = None


def run_job(
    store: Repository,
    job: Job,
    step_fns: dict[str, Callable[[], Any]],
) -> Job:
    """Run a job's steps in order, skipping completed ones, persisting state."""
    job.status = "running"
    store.put("job", job.id, _dump(job))
    try:
        for step in job.steps:
            if step in job.completed_steps:
                continue
            step_fns[step]()
            job.completed_steps.append(step)
            store.put("job", job.id, _dump(job))
        job.status = "done"
    except Exception as exc:  # a failed step leaves the job resumable
        job.status = "failed"
        job.error = f"{type(exc).__name__}: {exc}"
    store.put("job", job.id, _dump(job))
    return job


def _dump(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "kind": job.kind,
        "steps": job.steps,
        "completed_steps": job.completed_steps,
        "status": job.status,
        "error": job.error,
    }
