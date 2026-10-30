"""FastAPI application factory for SecondShift.

Why: one place registers every router under /api and loads settings and
providers at startup. Routers stay thin (spec section 17, rule 6).
Depends on: api/* routers, config, providers.registry.
"""

from fastapi import FastAPI

from secondshift.api import (
    ask,
    camera,
    captures,
    checkups,
    costs,
    custom,
    eval_routes,
    health,
    homes,
    packs,
    recheck,
    reports,
    reviews,
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
    from secondshift.watch.sources import CameraHub

    app.state.camera_hub = CameraHub()
    app.state.live_watches = {}

    @app.middleware("http")
    async def provider_mode_header(request, call_next):  # type: ignore[no-untyped-def]
        """Stamp every response with the provider mode (pass 2 Phase A).

        The frontend's persistent mock banner reads /api/settings, which
        returns the same value as the provider_mode field; the header
        makes the mode visible on ANY response for debugging/judges.
        """
        response = await call_next(request)
        mode = "mock" if app.state.settings.provider.value == "mock" else "live"
        response.headers["X-Provider-Mode"] = mode
        return response

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
        camera,
        reviews,
        homes,
    ):
        app.include_router(module.router, prefix="/api")
    app.include_router(custom.router, prefix="/api")
    from secondshift.api.v1 import build_v1_app

    app.mount(
        "/v1",
        build_v1_app(app.state.settings, app.state.providers, app.state.store),
    )
    return app


app = create_app()
