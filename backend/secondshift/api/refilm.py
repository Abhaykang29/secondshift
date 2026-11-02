"""Guided re-film router: POST a <=60s follow-up clip for a checkup;
its verdicts merge into the checkup's existing report (final pass,
item 1). Distinct from the re-check router: re-check compares a
later visit, re-film completes this one.
"""

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile

from secondshift.checklists.resolve import resolve_packs
from secondshift.core.refilm import refilm as core_refilm
from secondshift.domain.hazards import Report

router = APIRouter(tags=["refilm"])


@router.post("/checkups/{checkup_id}/refilm")
async def refilm_checkup(
    checkup_id: str, video: UploadFile, request: Request
) -> dict[str, Any]:
    """Upload a follow-up clip; returns the merged report."""
    store = request.app.state.store
    raw_report = store.get("report", checkup_id)
    if raw_report is None:
        raise HTTPException(status_code=404, detail="No report for this checkup yet.")
    previous = Report.model_validate(raw_report)
    packs = resolve_packs(store, previous.pack_ids)
    settings = request.app.state.settings
    work = Path(settings.data_dir) / checkup_id
    work.mkdir(parents=True, exist_ok=True)
    video_path = work / f"refilm-{uuid.uuid4().hex[:10]}.mp4"
    with video_path.open("wb") as handle:
        while chunk := await video.read(1 << 20):
            handle.write(chunk)
    try:
        merged = core_refilm(
            previous,
            str(video_path),
            packs,
            request.app.state.providers,
            settings,
            str(work),
            store=store,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return merged.model_dump(mode="json")
