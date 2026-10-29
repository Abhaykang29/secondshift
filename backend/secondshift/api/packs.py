"""Packs router.

Why: the frontend pack selector and the drift check need to read the real
loaded packs. Unlike the other routers this one is fully implemented in
Phase 0, because pack loading is Phase 0 scope.
Depends on: checklists.loader.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from secondshift.checklists.loader import load_all_packs

router = APIRouter(prefix="/packs", tags=["packs"])


@router.get("")
def list_packs() -> dict[str, Any]:
    """List all loaded packs with their item counts."""
    packs = load_all_packs()
    return {
        "packs": [
            {
                "pack_id": p.pack_id,
                "title": p.title,
                "audience": p.audience,
                "item_count": len(p.items),
                "status": p.status,
                "high_risk_zones": p.high_risk_zones,
            }
            for p in packs.values()
        ]
    }


@router.get("/{pack_id}")
def get_pack(pack_id: str) -> dict[str, Any]:
    """Return one full pack, or 404."""
    packs = load_all_packs()
    pack = packs.get(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Unknown pack {pack_id}")
    return pack.model_dump()
