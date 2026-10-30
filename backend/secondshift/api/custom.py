"""Custom checklists (Pass 3 P4, spec 5.3): bring your own checklist.

The user types 3-10 plain-English lines; Spark compiles each line
into a checklist item or refuses it with a reason. The compiled pack
is a DRAFT labelled "Custom checklist - not reviewed by an expert",
stored server-side so a normal check-up can run it by id. Draft
packs are excluded from eval.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from secondshift.core.compile import CUSTOM_LABEL, compile_checklist

router = APIRouter(prefix="/custom-checklists", tags=["custom"])


class CompileBody(BaseModel):
    lines: list[str]


def _summary(checklist: Any) -> dict[str, Any]:
    pack = checklist.pack
    return {
        "checklist_id": pack.pack_id,
        "label": CUSTOM_LABEL if checklist.source == "custom" else pack.title,
        "source": checklist.source,
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "kind": item.kind.value,
                "thin_object": item.thin_object,
                "sam_prompts": item.sam_prompts,
                "safety_prompts": item.safety_prompts,
            }
            for item in pack.items
        ],
        "refusals": checklist.refusals,
    }


@router.post("")
def compile_custom(body: CompileBody, request: Request) -> dict[str, Any]:
    lines = [line.strip() for line in body.lines if line.strip()]
    if not 3 <= len(lines) <= 10:
        raise HTTPException(
            status_code=422, detail="A custom checklist needs 3 to 10 lines."
        )
    checklist = compile_checklist(lines, vision=request.app.state.providers.vision)
    if not checklist.pack.items:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "None of those lines can be checked from video.",
                "refusals": checklist.refusals,
            },
        )
    request.app.state.store.put(
        "custom_pack",
        checklist.pack.pack_id,
        checklist.pack.model_dump(mode="json"),
    )
    return _summary(checklist)


@router.get("/{checklist_id}")
def get_custom(checklist_id: str, request: Request) -> dict[str, Any]:
    raw = request.app.state.store.get("custom_pack", checklist_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="No such custom checklist.")
    from secondshift.checklists.loader import Pack
    from secondshift.core.compile import Checklist

    pack = Pack.model_validate(raw)
    return _summary(Checklist(pack=pack, source="custom"))
