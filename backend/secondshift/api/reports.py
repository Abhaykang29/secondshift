"""Reports router: report JSON, printable HTML, share text, fix tracker.

Phase 3 replaces the Phase 0 stub. Visualization/before images are served
from the data dir by filename only (no path traversal).
Depends on: domain.hazards, reports.report, storage.
"""

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from secondshift.domain.hazards import Report
from secondshift.reports.report import render_html, share_text, whatsapp_link

router = APIRouter(prefix="/reports", tags=["reports"])


def _load_report(request: Request, checkup_id: str) -> Report:
    found: dict[str, Any] | None = request.app.state.store.get("report", checkup_id)
    if found is None:
        raise HTTPException(status_code=404, detail="No report yet - run a scan first.")
    return Report.model_validate(found)


@router.get("/{checkup_id}")
def get_report(checkup_id: str, request: Request) -> dict[str, Any]:
    """Return the report JSON."""
    return _load_report(request, checkup_id).model_dump(mode="json")


@router.get("/{checkup_id}/html", response_class=HTMLResponse)
def get_report_html(checkup_id: str, request: Request) -> str:
    """Return the printable HTML report."""
    return render_html(_load_report(request, checkup_id))


@router.get("/{checkup_id}/share")
def get_share(checkup_id: str, request: Request) -> dict[str, str]:
    """Return the prepared share text and WhatsApp link."""
    report = _load_report(request, checkup_id)
    raw = request.app.state.store.get("checkup", checkup_id) or {}
    label = raw.get("resident_label")
    return {"text": share_text(report, label), "whatsapp_url": whatsapp_link(report, label)}


@router.get("/{checkup_id}/image/{name}")
def get_image(checkup_id: str, name: str, request: Request) -> FileResponse:
    """Serve a visualization/before image by bare filename."""
    if "/" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Bad image name.")
    path = Path(request.app.state.settings.data_dir) / checkup_id / "viz" / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(str(path), media_type="image/png")


class FixUpdate(BaseModel):
    """A fix-tracker update."""

    status: Literal["todo", "done", "skipped"]
    note: str | None = None


@router.patch("/{checkup_id}/fixes/{fix_id}")
def update_fix(checkup_id: str, fix_id: str, body: FixUpdate, request: Request) -> dict[str, Any]:
    """Check off / skip a fix and persist the report."""
    report = _load_report(request, checkup_id)
    for card in report.fixes:
        if card.id == fix_id:
            card.status = body.status
            card.note = body.note
            request.app.state.store.put("report", checkup_id, report.model_dump(mode="json"))
            return card.model_dump(mode="json")
    raise HTTPException(status_code=404, detail=f"Unknown fix {fix_id}")
