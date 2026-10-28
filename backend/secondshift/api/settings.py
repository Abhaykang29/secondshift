"""Settings router: app info and the privacy controls (spec sections 7/12).

GET returns provider/cache mode/language list; DELETE /data is the
"Delete everything" button - it wipes the store and the data directory.
Depends on: storage, config.
"""

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/settings", tags=["settings"])

LANGUAGES = [
    {"code": "en", "label": "English"},
    {"code": "hi", "label": "Hindi (Devanagari - needs native review)"},
    {"code": "pa", "label": "Punjabi (TODO(TEAM): translation)"},
    {"code": "es", "label": "Spanish (TODO(TEAM): translation)"},
    {"code": "fr", "label": "French (TODO(TEAM): translation)"},
    {"code": "zh", "label": "Chinese (TODO(TEAM): translation)"},
    {"code": "ar", "label": "Arabic (TODO(TEAM): translation)"},
]


@router.get("")
def get_settings(request: Request) -> dict[str, Any]:
    """Current provider, cache mode, budget and supported languages."""
    settings = request.app.state.settings
    return {
        "provider": settings.provider.value,
        "cache_mode": settings.cache_mode.value,
        "budget_usd": settings.budget_usd,
        "verify_mode": settings.verify_mode,
        "languages": LANGUAGES,
        "translation_status": "English complete; Hindi draft (needs native review); "
        "other languages are TODO(TEAM).",
    }


@router.delete("/data")
def delete_everything(request: Request) -> dict[str, str]:
    """Delete all stored data: checkups, reports, captures, rules, events."""
    store = request.app.state.store
    store.delete_all()
    data_dir = Path(request.app.state.settings.data_dir)
    if data_dir.exists():
        for child in data_dir.iterdir():
            if child.name == "store.json":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    return {"status": "deleted"}
