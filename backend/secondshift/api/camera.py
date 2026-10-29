"""Camera WebSocket router: the phone-as-camera ingest (spec Phase 6.5).

The phone opens the /camera page, which streams JPEG frames as binary
WebSocket messages. Frames land in app.state.camera_hub; Watch's
PhoneSource consumes them. No frames are stored to disk here - the hub
is memory-only, matching the privacy model (frames, not recordings).
Depends on: fastapi WebSocket, watch.sources.CameraHub.
"""
import time
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["camera"])


@router.websocket("/camera")
async def camera_socket(websocket: WebSocket) -> None:
    """Receive JPEG frames from a phone browser and feed the hub."""
    await websocket.accept()
    hub = websocket.app.state.camera_hub
    started = time.monotonic()
    try:
        while True:
            data = await websocket.receive_bytes()
            hub.push_jpeg(data, at_s=time.monotonic() - started)
    except WebSocketDisconnect:
        return


@router.get("/camera/status")
def camera_status(request: Request) -> dict[str, Any]:
    """Whether any phone is currently feeding frames (hub depth probe)."""
    hub = request.app.state.camera_hub
    return {"queue_depth": hub._queue.qsize()}  # noqa: SLF001 - status probe
