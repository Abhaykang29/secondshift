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


@router.get("/honesty")
def honesty() -> dict[str, Any]:
    """The honesty numbers card data (final pass, item 2): read from
    eval/honesty.json, which scripts/honesty_report.py computes from
    stored results. 404 when the script has not been run - the app
    shows no numbers rather than invented ones."""
    import json as _json
    from pathlib import Path as _Path

    path = _Path(__file__).resolve().parents[3] / "eval" / "honesty.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Honesty numbers not computed yet.")
    data: dict[str, Any] = _json.loads(path.read_text())
    return data


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
    dataset = str(payload.get("dataset", ""))
    payload["labels_source"] = "mock" if "mock" in dataset.lower() else "real"
    return payload


@router.get("")
def list_runs(request: Request) -> dict[str, Any]:
    """List available eval runs (newest last)."""
    if not REPORTS_DIR.exists():
        return {"runs": []}
    return {"runs": sorted(p.name for p in REPORTS_DIR.iterdir() if p.is_dir())}
