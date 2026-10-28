"""Health router.

Why: the simplest possible proof the backend is up, used by `make dev`,
smoke tests and deployment checks.
Depends on: fastapi.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return service health."""
    return {"status": "ok", "service": "secondshift", "version": "0.1.0"}
