"""Watch router: sources (room-guarded), the demo run, and events.

The demo run compiles a sentence, then drives the engine over a scripted
synthetic timeline (gate open for 60 seconds) so the full Watch loop -
compile, gate, state machine, one alert - is visible before a real
camera exists. Real sources plug into the same engine via FileSource.
Depends on: watch.*, rules.compiler, privacy.room_guard, storage.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from secondshift.domain.enums import Primitive
from secondshift.domain.watch import WatchSource
from secondshift.privacy.room_guard import WatchRefused, assert_watch_allowed
from secondshift.providers.cost import CostGuard
from secondshift.rules.compiler import compile_rule
from secondshift.watch.engine import WatchEngine
from secondshift.watch.gate import ModelGate
from secondshift.watch.state_machine import StateMachine

router = APIRouter(prefix="/watch", tags=["watch"])


class CreateSource(BaseModel):
    """Request body for adding a watch source."""

    kind: str = "file"
    label: str
    room_type: str | None = None
    resident_consent: bool = False
    rtsp_url: str | None = None


@router.post("/sources")
def create_source(body: CreateSource, request: Request) -> dict[str, Any]:
    """Create a watch source; the room guard can refuse (bathroom, bedroom)."""
    source = WatchSource(
        id=uuid.uuid4().hex,
        kind=body.kind,  # type: ignore[arg-type]
        label=body.label,
        rtsp_url=body.rtsp_url,
        room_type=body.room_type,
        resident_consent=body.resident_consent,
        privacy_ok=body.room_type is not None and body.room_type != "bathroom",
    )
    try:
        assert_watch_allowed(source, body.room_type)
    except WatchRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # The RTSP URL is stored for the engine only and never returned in lists.
    request.app.state.store.put("watch_source", source.id, source.model_dump(mode="json"))
    return source.model_dump(mode="json", exclude={"rtsp_url"})


@router.get("/sources")
def list_sources(request: Request) -> dict[str, Any]:
    """List watch sources (RTSP URLs are never exposed)."""
    sources = [
        {k: v for k, v in s.items() if k != "rtsp_url"}
        for s in request.app.state.store.list("watch_source")
    ]
    return {"sources": sources}


class SimulateRun(BaseModel):
    """Body for the watch SIMULATION (scripted timeline - not a camera)."""

    rule_text: str
    mode_hint: str = "watch"


@router.post("/simulate")
def simulate(body: SimulateRun, request: Request) -> dict[str, Any]:
    """Simulation - not a camera: compile a rule, run a scripted timeline.

    Test/dev helper only (pass 2 Phase A). The real live loop is Phase G;
    this endpoint must never be presented as a camera feed.
    """
    spec = compile_rule(body.rule_text, body.mode_hint, request.app.state.providers.vision)
    if spec.status.value != "compiled":
        return {
            "spec": spec.model_dump(mode="json"),
            "events": [],
            "note": "The rule did not compile, so nothing was watched.",
        }
    duration_min = next(
        (c.duration_min for c in spec.conditions if c.primitive is Primitive.STATE_FOR_DURATION),
        None,
    )
    machine = StateMachine(source_id="demo-source", rule_id=spec.id)
    gate = ModelGate(CostGuard())
    engine = WatchEngine(machine, gate)
    if duration_min is not None:
        # Scripted timeline: closed 0-10s, open 10-70s, closed after.
        timeline = [(float(t), 10 <= t < 70) for t in range(0, 121, 5)]
        events = engine.run_duration_rule(timeline, duration_min * 60, "baby gate")
    else:
        timeline = [(float(t), t >= 200) for t in range(0, 121, 5)]
        events = engine.run_deadline_rule(timeline, 60.0, "pill box opening")
    store = request.app.state.store
    for event in events:
        store.put("watch_event", event.id, event.model_dump(mode="json"))
    return {
        "spec": spec.model_dump(mode="json"),
        "events": [e.model_dump(mode="json") for e in events],
        "alerts": sum(1 for e in events if e.state_to.value == "alert"),
        "ran_at": datetime.now(UTC).isoformat(),
    }


@router.get("/events")
def list_events(request: Request) -> dict[str, Any]:
    """List stored watch events in insertion order."""
    return {"events": request.app.state.store.list("watch_event")}


# --- Pass 2 Phase G: live watch sessions -------------------------------
class LiveStart(BaseModel):
    """Start a live watch: rule text + the phone source streaming frames."""

    rule_text: str
    source_id: str
    room_claim: str
    resident_consent: bool = False


@router.post("/live/start")
async def start_live_watch(
    body: LiveStart, request: Request
) -> dict[str, object]:
    """Compile the rule, classify the room, start consuming hub frames.

    NOT VERIFIED LIVE yet (needs a real phone + gate). The loop itself
    is unit-tested on synthetic frames with stub providers.
    """
    import asyncio

    from secondshift.rules.compiler import compile_rule
    from secondshift.watch.live import LiveWatch, classify_watch_room

    providers = request.app.state.providers
    hub = request.app.state.camera_hub
    spec = compile_rule(body.rule_text, "watch", providers.vision)
    if spec.status.value != "compiled":
        return {
            "started": False,
            "status": spec.status.value,
            "message": spec.refusal_reason or "The rule needs more detail.",
            "alternatives": spec.alternatives,
            "clarifying_question": spec.clarifying_question,
        }
    item = await asyncio.to_thread(hub.get, 2.0)
    if item is None:
        return {"started": False, "status": "no_frames",
                "message": "No camera frames yet - open /camera on the phone first."}
    _at, frame = item
    import cv2 as _cv2

    snap = Path(request.app.state.settings.data_dir) / "watch-room.jpg"
    snap.parent.mkdir(parents=True, exist_ok=True)
    _cv2.imwrite(str(snap), frame)
    room, allowed, reason = classify_watch_room(str(snap), body.room_claim, providers)
    if not allowed:
        return {"started": False, "status": "refused", "message": reason}
    if room == "bedroom" and not body.resident_consent:
        return {"started": False, "status": "consent_needed",
                "message": "Bedroom watches need the resident's explicit consent."}
    store = request.app.state.store
    sessions: dict[str, object] = request.app.state.live_watches

    def _record(event: object) -> None:
        store.append("watch_events", event.model_dump(mode="json"))  # type: ignore[attr-defined]

    watch = LiveWatch(
        spec, body.source_id, providers,
        str(Path(request.app.state.settings.data_dir) / "watch-live"),
        on_event=_record,
    )
    session_id = spec.id

    async def _run() -> None:
        while sessions.get(session_id) is watch:
            got = await asyncio.to_thread(hub.get, 2.0)
            if got is not None:
                watch.process_frame(got[1])

    sessions[session_id] = watch
    asyncio.create_task(_run())
    return {"started": True, "session_id": session_id, "room": room, "message": reason}


@router.post("/live/{session_id}/stop")
async def stop_live_watch(session_id: str, request: Request) -> dict[str, object]:
    """Stop a live watch session."""
    sessions: dict[str, object] = request.app.state.live_watches
    existed = sessions.pop(session_id, None) is not None
    return {"stopped": existed}


@router.get("/live/{session_id}/events")
async def live_watch_events(session_id: str, request: Request) -> object:
    """SSE stream of the session's events from the store."""
    from fastapi.responses import StreamingResponse

    store = request.app.state.store

    async def _stream() -> AsyncIterator[str]:
        import asyncio as _aio
        import json as _json

        seen = 0
        while True:
            events = [
                e for e in store.list("watch_events") if e.get("rule_id") == session_id
            ]
            for event in events[seen:]:
                yield f"data: {_json.dumps(event)}\n\n"
            seen = len(events)
            await _aio.sleep(1.0)

    return StreamingResponse(_stream(), media_type="text/event-stream")
