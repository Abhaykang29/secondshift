"""FastAPI application factory for SecondShift.

Why: one place registers every router under /api and loads settings and
providers at startup. Routers stay thin (spec section 17, rule 6).
Depends on: api/* routers, config, providers.registry.
"""

from fastapi import FastAPI

from secondshift.api import (
    ask,
    captures,
    checkups,
    costs,
    eval_routes,
    health,
    packs,
    recheck,
    reports,
    rules,
    scan,
    settings,
    watch,
)
from secondshift.config import Settings
from secondshift.providers.registry import build_providers


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(title="SecondShift", version="0.1.0")
    app.state.settings = Settings.load()
    app.state.providers = build_providers(app.state.settings)
    from pathlib import Path

    from secondshift.storage.repository import Repository

    app.state.store = Repository(Path(app.state.settings.data_dir) / "store.json")
    for module in (
        health,
        packs,
        checkups,
        captures,
        reports,
        rules,
        watch,
        ask,
        costs,
        eval_routes,
        settings,
        scan,
        recheck,
    ):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
