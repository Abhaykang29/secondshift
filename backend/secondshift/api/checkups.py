"""Checkups router: create and read checkups.

Why: a Checkup is created with consent BEFORE any capture exists
(spec section 14). Handlers stay thin - storage via the repository.
Depends on: fastapi, domain.checkup, storage.repository.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from secondshift.domain.checkup import Checkup, Consent

router = APIRouter(prefix="/checkups", tags=["checkups"])


class CreateCheckup(BaseModel):
    """Request body for creating a checkup."""

    pack_ids: list[str]
    resident_label: str | None = None
    language: str = "en"
    consent: Consent


@router.post("")
def create_checkup(body: CreateCheckup, request: Request) -> dict[str, Any]:
    """Create a checkup. Consent must be affirmative on both checkboxes."""
    if not (body.consent.resident_informed and body.consent.no_private_moments):
        raise HTTPException(
            status_code=422,
            detail="Consent is required: the resident must know and agree, "
            "and no one may be filmed in a bathroom or undressed.",
        )
    if not 1 <= len(body.pack_ids) <= 3:
        raise HTTPException(status_code=422, detail="Choose between 1 and 3 packs per check-up.")
    checkup = Checkup(
        id=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        pack_ids=body.pack_ids,
        resident_label=body.resident_label,
        language=body.language,
        consent=body.consent,
    )
    request.app.state.store.put("checkup", checkup.id, checkup.model_dump(mode="json"))
    return checkup.model_dump(mode="json")


@router.get("")
def list_checkups(request: Request) -> dict[str, Any]:
    """List all checkups."""
    return {"checkups": request.app.state.store.list("checkup")}


@router.get("/{checkup_id}")
def get_checkup(checkup_id: str, request: Request) -> dict[str, Any]:
    """Fetch one checkup or 404."""
    found: dict[str, Any] | None = request.app.state.store.get("checkup", checkup_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"Unknown checkup {checkup_id}")
    return found
