"""Watch router: sources (room-guarded), the demo run, and events.

The demo run compiles a sentence, then drives the engine over a scripted
synthetic timeline (gate open for 60 seconds) so the full Watch loop -
compile, gate, state machine, one alert - is visible before a real
camera exists. Real sources plug into the same engine via FileSource.
Depends on: watch.*, rules.compiler, privacy.room_guard, storage.
"""

import uuid
from datetime import UTC, datetime
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
    spec = compile_rule(body.rule_text, body.mode_hint)
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
