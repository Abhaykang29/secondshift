"""Homes router: the places list (Pass 3 spec 4.5).

A "home" is a home_label shared by one or more checkups. The list
shows each place's last check, open fixes and re-check due date
(last check + 30 days). Deleting a place deletes every checkup,
report, capture and file for that label in one action.
Depends on: storage repository.
"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/homes", tags=["homes"])

_RECHECK_DAYS = 30


@router.get("")
def list_homes(request: Request) -> dict[str, Any]:
    store = request.app.state.store
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw in store.list("checkup"):
        grouped.setdefault(str(raw.get("home_label") or "Home"), []).append(raw)
    homes: list[dict[str, Any]] = []
    for label, checkups in sorted(grouped.items()):
        checkups.sort(key=lambda c: str(c.get("created_at", "")))
        latest = checkups[-1]
        report = store.get("report", str(latest.get("id"))) or {}
        last_at = str(latest.get("created_at", ""))
        try:
            due = (
                datetime.fromisoformat(last_at) + timedelta(days=_RECHECK_DAYS)
            ).isoformat()
        except ValueError:
            due = ""
        homes.append(
            {
                "label": label,
                "checkup_ids": [str(c.get("id")) for c in checkups],
                "last_check_at": last_at,
                "last_checkup_id": str(latest.get("id")),
                "pack_ids": latest.get("pack_ids", []),
                "open_fixes": sum(
                    1 for f in report.get("fixes", []) if f.get("status") == "todo"
                ),
                "open_findings": sum(
                    1
                    for h in report.get("hazards", [])
                    if h.get("verification") in ("confirmed", "needs_human")
                ),
                "recheck_due": due,
            }
        )
    return {"homes": homes}


@router.delete("/{label}")
def delete_home(label: str, request: Request) -> dict[str, Any]:
    """Delete a place and ALL of its data (checkups, reports, files)."""
    store = request.app.state.store
    targets = [
        raw
        for raw in store.list("checkup")
        if str(raw.get("home_label") or "Home") == label
    ]
    if not targets:
        raise HTTPException(status_code=404, detail="No such home.")
    data_dir = Path(request.app.state.settings.data_dir)
    deleted_records = 0
    for raw in targets:
        checkup_id = str(raw.get("id"))
        for capture in store.list("capture"):
            if str(capture.get("checkup_id")) == checkup_id:
                capture_id = str(capture.get("id"))
                deleted_records += store.delete("capture", capture_id)
                deleted_records += store.delete("keyframes", capture_id)
                deleted_records += store.delete("audio", capture_id)
                shutil.rmtree(data_dir / capture_id, ignore_errors=True)
        for kind in ("checkup", "report", "job", "recheck"):
            deleted_records += store.delete(kind, checkup_id)
        shutil.rmtree(data_dir / checkup_id, ignore_errors=True)
    return {"deleted_checkups": len(targets), "deleted_records": deleted_records}
