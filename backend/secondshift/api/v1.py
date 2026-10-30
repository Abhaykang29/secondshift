"""Public engine API (/v1) - Pass 3 P4, spec 5.2.

A mounted sub-application with its own OpenAPI (/v1/openapi.json,
/v1/docs). Auth: X-API-Key header; keys come from V1_API_KEYS
("name:key,..."); when unset, one local development key is accepted
(local only - documented in docs/ENGINE.md). Rate limit: 30 requests
per minute per key. All model spend flows through the same transport
cost guard and budget as the app.

Checks run the engine (secondshift.core) in a worker thread; poll
GET /v1/checks/{id} for the result.
"""

import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from secondshift.config import Settings
from secondshift.core import check as core_check
from secondshift.core import compile_checklist, compile_rule
from secondshift.core import recheck as core_recheck
from secondshift.providers.registry import Providers
from secondshift.storage.repository import Repository

_RATE_LIMIT = 30
_RATE_WINDOW_S = 60.0


def _parse_keys(settings: Settings) -> dict[str, str]:
    keys: dict[str, str] = {}
    for pair in settings.v1_api_keys.split(","):
        pair = pair.strip()
        if ":" in pair:
            name, key = pair.split(":", 1)
            keys[key.strip()] = name.strip()
    return keys or {"local-dev-key": "local"}


class ChecklistBody(BaseModel):
    pack_ids: list[str] = []
    lines: list[str] = []


class RuleBody(BaseModel):
    sentence: str


def build_v1_app(settings: Settings, providers: Providers, store: Repository) -> FastAPI:
    app = FastAPI(title="SecondShift Engine API", version="1.0.0")
    keys = _parse_keys(settings)
    hits: dict[str, list[float]] = {}
    jobs: dict[str, dict[str, Any]] = {}
    lock = threading.Lock()

    def require_key(x_api_key: str = Header(default="")) -> str:
        if x_api_key not in keys:
            raise HTTPException(status_code=401, detail="Unknown API key.")
        now = time.monotonic()
        with lock:
            window = [t for t in hits.get(x_api_key, []) if now - t < _RATE_WINDOW_S]
            if len(window) >= _RATE_LIMIT:
                raise HTTPException(
                    status_code=429, detail="Rate limit: 30 requests per minute."
                )
            window.append(now)
            hits[x_api_key] = window
        return keys[x_api_key]

    @app.post("/checklists")
    def create_checklist(
        body: ChecklistBody, _client: str = Depends(require_key)
    ) -> dict[str, Any]:
        source = list(body.pack_ids) + list(body.lines)
        if not source:
            raise HTTPException(status_code=422, detail="Give pack_ids and/or lines.")
        checklist = compile_checklist(source, vision=providers.vision)
        if checklist.source == "custom":
            store.put(
                "custom_pack",
                checklist.pack.pack_id,
                checklist.pack.model_dump(mode="json"),
            )
        pack = checklist.pack
        return {
            "checklist_id": pack.pack_id,
            "source": checklist.source,
            "label": checklist.label,
            "items": [item.model_dump(mode="json") for item in pack.items],
            "refusals": checklist.refusals,
        }

    def _run_check(job_id: str, video_path: str, checklist_id: str) -> None:
        try:
            from secondshift.checklists.resolve import resolve_pack

            pack = resolve_pack(store, checklist_id)
            if pack is None:
                raise ValueError(f"Unknown checklist {checklist_id}")
            from secondshift.core.compile import Checklist

            checklist = Checklist(
                pack=pack, source="custom" if pack.pack_id.startswith("custom-") else "packs"
            )
            work = Path(settings.data_dir) / "v1" / job_id
            report = core_check(
                video_path, checklist, providers, settings, str(work), store=store
            )
            with lock:
                jobs[job_id].update(
                    status="done", report=report.model_dump(mode="json")
                )
        except Exception as exc:  # surfaced to the poller, never hidden
            with lock:
                jobs[job_id].update(status="error", error=str(exc))

    @app.post("/checks")
    async def create_check(
        video: UploadFile = File(...),  # noqa: B008
        checklist_id: str = Form(...),
        _client: str = Depends(require_key),
    ) -> dict[str, Any]:
        job_id = uuid.uuid4().hex
        work = Path(settings.data_dir) / "v1" / job_id
        work.mkdir(parents=True, exist_ok=True)
        video_path = work / f"video{Path(video.filename or 'video.mp4').suffix or '.mp4'}"
        video_path.write_bytes(await video.read())
        with lock:
            jobs[job_id] = {"status": "running", "checklist_id": checklist_id}
        threading.Thread(
            target=_run_check, args=(job_id, str(video_path), checklist_id), daemon=True
        ).start()
        return {"job_id": job_id, "status": "running"}

    @app.get("/checks/{job_id}")
    def get_check(job_id: str, _client: str = Depends(require_key)) -> dict[str, Any]:
        with lock:
            job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="No such check.")
        return job

    @app.post("/checks/{job_id}/recheck")
    async def recheck_check(
        job_id: str,
        video: UploadFile = File(...),  # noqa: B008
        _client: str = Depends(require_key),
    ) -> dict[str, Any]:
        with lock:
            previous = jobs.get(job_id)
        if previous is None or previous.get("status") != "done":
            raise HTTPException(status_code=409, detail="The original check is not done.")
        new_id = uuid.uuid4().hex
        work = Path(settings.data_dir) / "v1" / new_id
        work.mkdir(parents=True, exist_ok=True)
        video_path = work / f"video{Path(video.filename or 'video.mp4').suffix or '.mp4'}"
        video_path.write_bytes(await video.read())

        def _run() -> None:
            try:
                from secondshift.checklists.resolve import resolve_pack
                from secondshift.core.compile import Checklist
                from secondshift.domain.hazards import Report

                pack = resolve_pack(store, str(previous["checklist_id"]))
                if pack is None:
                    raise ValueError("Original checklist no longer exists")
                checklist = Checklist(pack=pack, source="packs")
                result = core_recheck(
                    Report.model_validate(previous["report"]),
                    str(video_path),
                    checklist,
                    providers,
                    settings,
                    str(work),
                )
                with lock:
                    jobs[new_id].update(
                        status="done", recheck=result.model_dump(mode="json")
                    )
            except Exception as exc:
                with lock:
                    jobs[new_id].update(status="error", error=str(exc))

        with lock:
            jobs[new_id] = {"status": "running", "checklist_id": previous["checklist_id"]}
        threading.Thread(target=_run, daemon=True).start()
        return {"job_id": new_id, "status": "running"}

    @app.post("/rules/compile")
    def compile_rule_endpoint(
        body: RuleBody, _client: str = Depends(require_key)
    ) -> dict[str, Any]:
        spec = compile_rule(body.sentence, vision=providers.vision)
        return spec.model_dump(mode="json")

    return app
