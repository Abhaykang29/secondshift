"""Reports router - stubbed in Phase 0.

Why: Phase 0 fixes the API surface (routes exist, contract is stable) so
the frontend and workers can build against it. Real handlers land in
Phase 3. Every stub returns 501 with a clear message, never fake data.
Depends on: fastapi.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_stub() -> dict[str, str]:
    """Stub: list reports (Phase 0)."""
    raise HTTPException(status_code=501, detail="Not implemented yet - Phase 3.")
