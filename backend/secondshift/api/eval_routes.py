"""Eval router: the latest harness run for the /eval page.

Returns the newest eval/reports/*/results.json. If no run exists, the
page gets an honest empty state (501 was the Phase 0 stub behaviour).
Depends on: stdlib only.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/eval", tags=["eval"])

REPORTS_DIR = Path(__file__).parents[3] / "eval" / "reports"


@router.get("/latest")
def latest(request: Request) -> dict[str, Any]:
    """Return the newest eval run's results.json."""
    if not REPORTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No eval run yet - run make eval.")
    runs = sorted(p for p in REPORTS_DIR.iterdir() if (p / "results.json").exists())
    if not runs:
        raise HTTPException(status_code=404, detail="No eval run yet - run make eval.")
    payload: dict[str, Any] = json.loads((runs[-1] / "results.json").read_text())
    payload["run_dir"] = runs[-1].name
    return payload


@router.get("")
def list_runs(request: Request) -> dict[str, Any]:
    """List available eval runs (newest last)."""
    if not REPORTS_DIR.exists():
        return {"runs": []}
    return {"runs": sorted(p.name for p in REPORTS_DIR.iterdir() if p.is_dir())}
