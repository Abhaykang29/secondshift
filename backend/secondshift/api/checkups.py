"""Checkups router - stubbed in Phase 0.

Why: Phase 0 fixes the API surface (routes exist, contract is stable) so
the frontend and workers can build against it. Real handlers land in
Phase 1-2. Every stub returns 501 with a clear message, never fake data.
Depends on: fastapi.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/checkups", tags=["checkups"])


@router.get("")
def list_stub() -> dict[str, str]:
    """Stub: list checkups (Phase 0)."""
    raise HTTPException(status_code=501, detail="Not implemented yet - Phase 1-2.")
