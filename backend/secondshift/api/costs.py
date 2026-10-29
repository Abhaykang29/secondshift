"""Costs router.

Why: the dev cost badge (spec section 11.4) reads cumulative spend and the
ledger from the cost guard. Phase 0 returns an empty ledger.
Depends on: providers.cost (wired via app state in Phase 2).
"""

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("")
def get_costs(request: Request) -> dict[str, Any]:
    """Cumulative spend from the persistent SQLite ledger (Phase B).

    Totals by model and by phase_tag, plus the most recent call rows.
    Survives restarts because the budget guard sums the same table.
    """
    from pathlib import Path

    from secondshift.providers import ledger

    db = Path(request.app.state.settings.data_dir) / "costs.db"
    if not db.exists():
        return {"spent_usd": 0.0, "call_count": 0, "by_model": {}, "by_phase": {}, "records": []}
    conn = ledger.connect(db)
    records = ledger.recent(conn, 50)
    return {
        "spent_usd": ledger.total(conn),
        "call_count": len(records),
        "by_model": ledger.totals_by(conn, "model"),
        "by_phase": ledger.totals_by(conn, "phase_tag"),
        "records": records,
    }
