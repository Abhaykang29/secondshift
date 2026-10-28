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


class PhoneSource:
    """An old phone on WiFi serving MJPEG/snapshots (Phase 6.5).

    TODO(TEAM): pick the phone app / endpoint with the team; the engine
    only needs frames(), so this stays a contained change.
    """

    def __init__(self, snapshot_url: str) -> None:
        self.snapshot_url = snapshot_url

    def frames(self) -> Iterator[tuple[float, np.ndarray]]:
        """Not yet wired - see TODO(TEAM) in the class docstring."""
        raise NotImplementedError("PhoneSource lands in Phase 6.5 with the team's phone setup.")


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
