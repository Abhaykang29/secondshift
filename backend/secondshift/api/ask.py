"""Ask router: questions about THIS check-up's report (spec section 5.1).

Scope is strict: answers come only from the check-up's own report -
a hazard's fix, its evidence, or the cannot-assess list. Anything else
gets the honest out-of-scope answer; general home-safety Q&A is a
different, larger product and is not faked here.
Depends on: domain.hazards, reports data in the store.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from secondshift.domain.hazards import Report

router = APIRouter(prefix="/ask", tags=["ask"])

_OUT_OF_SCOPE = (
    "I can only answer questions about this check-up's report - for example "
    "'How do I fix the rug?' or 'How sure are you about the bathroom?'"
)


class AskRequest(BaseModel):
    """A question about one checkup's report."""

    checkup_id: str
    question: str


@router.post("")
def ask(body: AskRequest, request: Request) -> dict[str, Any]:
    """Answer a question from the report's own data, or say it's out of scope."""
    raw = request.app.state.store.get("report", body.checkup_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="No report for this checkup yet.")
    report = Report.model_validate(raw)
    question = body.question.lower()
    # Keyword-match against hazard titles/items in THIS report.
    for hazard in report.hazards:
        keywords = set(hazard.title.lower().split()) | {hazard.item_id.lower()}
        if (
            any(word in question for word in keywords if len(word) > 3)
            or hazard.room in question
            and hazard.room in hazard.title.lower()
        ):
            fix = next((f for f in report.fixes if f.hazard_id == hazard.id), None)
            answer = f"{hazard.title} ({hazard.room}): {hazard.verification_reason}"
            if fix:
                answer += f" The fix: {fix.chosen.title} - {fix.chosen.how}"
            return {
                "answer": answer,
                "hazard_id": hazard.id,
                "follow_up": "Want the step-by-step fix card? Open the fix tracker.",
            }
    if "check" in question or "miss" in question or "couldn't" in question:
        areas = "; ".join(f"{c.area}: {c.detail}" for c in report.cannot_assess)
        return {
            "answer": f"Things I couldn't check: {areas or 'nothing - everything was visible.'}",
            "hazard_id": None,
            "follow_up": None,
        }
    if "first" in question or "start" in question:
        titles = {h.id: h.title for h in report.hazards}
        top = [titles.get(hid, hid) for hid in report.fix_first[:3]]
        return {
            "answer": "Fix these first: " + ", ".join(top) + ".",
            "hazard_id": None,
            "follow_up": None,
        }
    return {"answer": _OUT_OF_SCOPE, "hazard_id": None, "follow_up": None}
