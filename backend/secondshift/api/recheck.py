"""Re-check router: run a new scan for a checkup and diff it (spec 9.11).

Also evaluates the checkup's saved check-up rules on the new capture.
Depends on: recheck.diff, rules.evaluate_checkup, pipeline.scan.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from secondshift.checklists.loader import load_all_packs
from secondshift.domain.checkup import Checkup, Keyframe
from secondshift.domain.hazards import Report
from secondshift.domain.rules import RuleSpec
from secondshift.pipeline.scan import ScanInput, run_scan
from secondshift.recheck.diff import diff_scans
from secondshift.rules.evaluate_checkup import evaluate_checkup_rule

router = APIRouter(tags=["recheck"])


class RecheckRequest(BaseModel):
    """Body for a re-check: the scenario/capture to diff against."""

    scenario: str = "parent_home_fixed"
    capture_id: str = "recheck-demo"


@router.post("/checkups/{checkup_id}/recheck")
def start_recheck(checkup_id: str, body: RecheckRequest, request: Request) -> dict[str, Any]:
    """Run the re-check scan, diff it, evaluate saved rules, store + return."""
    store = request.app.state.store
    raw_checkup = store.get("checkup", checkup_id)
    raw_report = store.get("report", checkup_id)
    if raw_checkup is None or raw_report is None:
        raise HTTPException(status_code=404, detail="Need a checkup with a report first.")
    checkup = Checkup.model_validate(raw_checkup)
    previous_report = Report.model_validate(raw_report)
    packs_by_id = load_all_packs()
    packs = [packs_by_id[pid] for pid in checkup.pack_ids if pid in packs_by_id]
    keyframes = [
        Keyframe(
            id=f"recheck-kf-{i:03d}",
            capture_id=body.capture_id,
            t=float(i * 5),
            image_path="",
            sharpness=500.0,
            brightness=120.0,
            usable=True,
        )
        for i in range(20)
    ]
    output = run_scan(
        request.app.state.providers,
        ScanInput(
            checkup=checkup,
            packs=packs,
            keyframes=keyframes,
            scenario_name=body.scenario,
            verify_mode=request.app.state.settings.verify_mode,
        ),
    )
    recheck = diff_scans(checkup_id, body.capture_id, previous_report.hazards, output)
    # Evaluate this checkup's saved check-up rules on the new capture.
    for raw_rule in store.list("rule"):
        if raw_rule.get("checkup_id") != checkup_id:
            continue
        spec_payload = {k: v for k, v in raw_rule.items() if k != "checkup_id"}
        try:
            spec = RuleSpec.model_validate(spec_payload)
        except Exception:
            continue
        if spec.status.value != "compiled":
            continue
        outcome = evaluate_checkup_rule(
            spec,
            request.app.state.providers.segmenter,
            request.app.state.providers.vision,
            keyframes,
            output.rooms_seen,
        )
        recheck.rule_outcomes.append(outcome)
    store.put("recheck", recheck.id, recheck.model_dump(mode="json"))
    return recheck.model_dump(mode="json")
