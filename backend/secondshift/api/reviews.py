"""Reviews router: in-app Right/Wrong marks and missed-item notes.

Pass 3 (spec 4.6 + P1.6): every mark becomes an eval label on disk
under eval/datasets/real/ - one JSONL file per checkup plus a
manifest - which is how the eval harness gets REAL labels instead of
invented ones. Labels are append-only; the count endpoint powers the
"Your reviews: N findings labeled" badge.
Depends on: storage (report lookup for item stamping).
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["reviews"])

_LABELS_DIR = Path(__file__).resolve().parents[3] / "eval" / "datasets" / "real"


def labels_dir() -> Path:
    _LABELS_DIR.mkdir(parents=True, exist_ok=True)
    return _LABELS_DIR


def _append(checkup_id: str, entry: dict[str, Any]) -> None:
    entry = {"checkup_id": checkup_id, "at": datetime.now(UTC).isoformat(), **entry}
    path = labels_dir() / f"{checkup_id}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    _refresh_manifest()


def _all_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(labels_dir().glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
    return entries


def _refresh_manifest() -> None:
    entries = _all_entries()
    manifest = {
        "labels": len(entries),
        "verdicts": sum(1 for e in entries if e.get("type") == "verdict"),
        "missed": sum(1 for e in entries if e.get("type") == "missed"),
        "checkups": sorted({str(e.get("checkup_id")) for e in entries}),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    (labels_dir() / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


class VerdictBody(BaseModel):
    hazard_id: str
    mark: Literal["right", "wrong"]


class MissedBody(BaseModel):
    item_id: str
    room: str = ""
    timestamp_s: float | None = None


@router.post("/checkups/{checkup_id}/reviews")
def post_verdict(checkup_id: str, body: VerdictBody, request: Request) -> dict[str, Any]:
    """Record a Right/Wrong mark on one finding, stamped with its item."""
    report = request.app.state.store.get("report", checkup_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No report for that checkup.")
    hazard = next(
        (h for h in report.get("hazards", []) if h.get("id") == body.hazard_id), None
    )
    _append(
        checkup_id,
        {
            "type": "verdict",
            "hazard_id": body.hazard_id,
            "item_id": hazard.get("item_id") if hazard else None,
            "room": hazard.get("room") if hazard else None,
            "verification": hazard.get("verification") if hazard else None,
            "mark": body.mark,
        },
    )
    return {"stored": True, "total_labels": len(_all_entries())}


@router.post("/checkups/{checkup_id}/missed")
def post_missed(checkup_id: str, body: MissedBody, request: Request) -> dict[str, Any]:
    """Record a 'something it missed' note (item + room + timestamp)."""
    if request.app.state.store.get("checkup", checkup_id) is None:
        raise HTTPException(status_code=404, detail="No such checkup.")
    _append(
        checkup_id,
        {
            "type": "missed",
            "item_id": body.item_id,
            "room": body.room,
            "timestamp_s": body.timestamp_s,
        },
    )
    return {"stored": True, "total_labels": len(_all_entries())}


@router.get("/checkups/{checkup_id}/reviews")
def get_reviews(checkup_id: str) -> dict[str, Any]:
    entries = [e for e in _all_entries() if e.get("checkup_id") == checkup_id]
    return {"labels": entries, "count": len(entries)}


@router.get("/reviews/summary")
def get_summary() -> dict[str, Any]:
    entries = _all_entries()
    return {
        "total_labels": len(entries),
        "verdicts": sum(1 for e in entries if e.get("type") == "verdict"),
        "missed": sum(1 for e in entries if e.get("type") == "missed"),
        "checkups": len({e.get("checkup_id") for e in entries}),
    }
