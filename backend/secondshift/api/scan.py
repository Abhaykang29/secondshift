"""Scan router: run a check-up scan and read its report.

Phase 2 wires the pipeline to the API. If the capture has stored
keyframes they are used; otherwise (demo/tests) keyframes are synthesized
from the mock scenario's timestamps so the demo flow works with no video.
Depends on: pipeline.scan, checklists.loader, storage.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from secondshift.checklists.loader import load_all_packs
from secondshift.domain.checkup import Checkup, Keyframe
from secondshift.pipeline.scan import ScanInput, run_scan_job

router = APIRouter(tags=["scan"])


class ScanRequest(BaseModel):
    """Body for starting a scan."""

    capture_id: str | None = None
    scenario: str | None = None


@router.post("/checkups/{checkup_id}/scan")
def start_scan(checkup_id: str, body: ScanRequest, request: Request) -> dict[str, Any]:
    """Run the scan pipeline for a checkup and return its report."""
    store = request.app.state.store
    raw = store.get("checkup", checkup_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Unknown checkup {checkup_id}")
    checkup = Checkup.model_validate(raw)
    packs_by_id = load_all_packs()
    packs = [packs_by_id[pid] for pid in checkup.pack_ids if pid in packs_by_id]
    keyframes: list[Keyframe] = []
    if body.capture_id:
        stored = store.get("keyframes", body.capture_id)
        if stored:
            keyframes = [Keyframe.model_validate(k) for k in stored["keyframes"]]
    scenario = body.scenario
    if not keyframes:
        # Demo path: no real capture yet - keyframes at 5s intervals.
        scenario = scenario or (
            "baby_home_demo" if checkup.pack_ids == ["babyproofing"] else "parent_home_demo"
        )
        keyframes = [
            Keyframe(
                id=f"demo-kf-{i:03d}",
                capture_id="demo",
                t=float(i * 5),
                image_path="",
                sharpness=500.0,
                brightness=120.0,
                usable=True,
            )
            for i in range(20)
        ]
    # Pass 2 Phase E.4: person-blur every real keyframe BEFORE the scan
    # reads it (spec 14.3). Demo keyframes have no files and are skipped.
    # A segmentation failure returns -1: the frame still scans (the scan
    # itself is not the privacy surface), but visualize.py must then use
    # the blur-all-but fallback for any image it writes.
    if keyframes and keyframes[0].image_path:
        from secondshift.privacy.blur import blur_persons

        for kf in keyframes:
            if kf.image_path:
                blur_persons(kf.image_path, request.app.state.providers.segmenter)
    if scenario is None and request.app.state.settings.provider.value == "mock":
        scenario = "baby_home_demo" if checkup.pack_ids == ["babyproofing"] else "parent_home_demo"
    if scenario is not None:
        for provider in (
            request.app.state.providers.vision,
            request.app.state.providers.segmenter,
            request.app.state.providers.transcriber,
        ):
            if hasattr(provider, "scenario_name"):
                setattr(provider, "scenario_name", scenario)
    narration_facts = []
    try:
        from secondshift.capture.narration import extract_facts

        segments = request.app.state.providers.transcriber.transcribe("demo", checkup.language)
        narration_facts = extract_facts(segments)
    except Exception:
        narration_facts = []
    scan_input = ScanInput(
        checkup=checkup,
        packs=packs,
        keyframes=keyframes,
        scenario_name=scenario,
        narration_facts=narration_facts,
        verify_mode=request.app.state.settings.verify_mode,
    )
    job, report = run_scan_job(
        store,
        request.app.state.providers,
        scan_input,
        data_dir=request.app.state.settings.data_dir,
    )
    return {"job_id": job.id, "job_status": job.status, "report": report.model_dump(mode="json")}


@router.get("/checkups/{checkup_id}/report")
def get_report(checkup_id: str, request: Request) -> dict[str, Any]:
    """Return the stored report for a checkup."""
    found: dict[str, Any] | None = request.app.state.store.get("report", checkup_id)
    if found is None:
        raise HTTPException(status_code=404, detail="No report yet - run a scan first.")
    return found


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> dict[str, Any]:
    """Return one job's status (processing page polling)."""
    found: dict[str, Any] | None = request.app.state.store.get("job", job_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {job_id}")
    return found
