"""Costs router.

Why: the dev cost badge (spec section 11.4) reads cumulative spend and the
ledger from the cost guard. Phase 0 returns an empty ledger.
Depends on: providers.cost (wired via app state in Phase 2).
"""

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("")
def get_costs() -> dict[str, Any]:
    """Return cumulative spend and call count (empty in Phase 0)."""
    return {"spent_usd": 0.0, "call_count": 0, "records": []}
