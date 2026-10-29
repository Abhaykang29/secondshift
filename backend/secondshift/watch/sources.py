"""Watch frame sources (spec sections 9.14 / 6).

One interface (frames with timestamps) behind three sources: a file
(FileSource - used by tests and the demo), a phone (Phase 6.5: the LAN
snapshot endpoint), and RTSP (TODO(API)-adjacent, LAN cameras).
Depends on: opencv, numpy.
"""

from collections.abc import Iterator
from typing import Protocol

import cv2
import numpy as np


class FrameSource(Protocol):
    """Anything that yields (timestamp_seconds, BGR frame) pairs."""

    def frames(self) -> Iterator[tuple[float, np.ndarray]]:
        """Yield frames in timestamp order."""
        ...


class FileSource:
    """Reads a video file at its native frame rate (timestamps in seconds)."""

    def __init__(self, path: str) -> None:
        self.path = path

    def frames(self) -> Iterator[tuple[float, np.ndarray]]:
        """Yield (t, frame) for every frame in the file."""
        cap = cv2.VideoCapture(self.path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield index / fps, frame
            index += 1
        cap.release()


class CameraHub:
    """In-process frame hub fed by the /camera WebSocket (api/camera.py).

    The phone's browser page streams JPEG frames over the WebSocket; the
    hub decodes and keeps the latest frames for any PhoneSource consumer.
    Bounded queue: a slow consumer never grows memory.
    """

    def __init__(self, max_frames: int = 120) -> None:
        import queue as _queue

        self._queue: _queue.Queue[tuple[float, np.ndarray]] = _queue.Queue(maxsize=max_frames)

    def push_jpeg(self, data: bytes, at_s: float) -> bool:
        """Decode one JPEG frame and queue it; False if undecodable/full."""
        import queue as _queue

        array = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            return False
        try:
            self._queue.put_nowait((at_s, frame))
            return True
        except _queue.Full:
            return False

    def get(self, timeout_s: float = 5.0) -> tuple[float, np.ndarray] | None:
        """Next frame, or None on timeout."""
        import queue as _queue

        try:
            return self._queue.get(timeout=timeout_s)
        except _queue.Empty:
            return None


class PhoneSource:
    """An old phone streaming frames via the /camera page + WebSocket.

    The phone opens https://<this-machine>:8000/camera-page (or the Vite
    page at /camera) in Safari/Chrome, allows the camera, and the page
    sends JPEG frames over the WebSocket to the backend hub. frames()
    consumes the hub - the engine never knows the transport.
    """

    def __init__(self, hub: CameraHub) -> None:
        self.hub = hub

    def frames(self) -> Iterator[tuple[float, np.ndarray]]:
        """Yield frames from the hub until it goes quiet for 30s."""
        import time as _time

        quiet_since: float | None = None
        while True:
            item = self.hub.get(timeout_s=5.0)
            if item is None:
                if quiet_since is None:
                    quiet_since = _time.monotonic()
                elif _time.monotonic() - quiet_since > 30.0:
                    return
                continue
            quiet_since = None
            yield item


class RtspSource:
    """An RTSP camera on the LAN. The URL is never logged (PRIVACY.md)."""

    def __init__(self, url: str) -> None:
        self.url = url

    def frames(self) -> Iterator[tuple[float, np.ndarray]]:
        """Stream frames via OpenCV's RTSP support."""
        cap = cv2.VideoCapture(self.url)
        fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield index / fps, frame
            index += 1
        cap.release()
