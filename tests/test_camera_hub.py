"""Camera hub tests (Phase 6.5): JPEG frames in, frames out; junk rejected."""

import cv2
import numpy as np
from secondshift.watch.sources import CameraHub, PhoneSource


def _jpeg_bytes() -> bytes:
    frame = np.full((48, 64, 3), 120, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", frame)
    assert ok
    return encoded.tobytes()


def test_hub_round_trip() -> None:
    """A pushed JPEG comes back as a decoded frame with its timestamp."""
    hub = CameraHub()
    assert hub.push_jpeg(_jpeg_bytes(), at_s=1.5)
    item = hub.get(timeout_s=1.0)
    assert item is not None
    t, frame = item
    assert t == 1.5 and frame.shape == (48, 64, 3)


def test_hub_rejects_undecodable_bytes() -> None:
    """Non-image bytes are dropped, never queued."""
    hub = CameraHub()
    assert not hub.push_jpeg(b"not a jpeg", at_s=0.0)
    assert hub.get(timeout_s=0.2) is None


def test_phone_source_consumes_hub_frames() -> None:
    """PhoneSource yields what the hub received."""
    hub = CameraHub()
    hub.push_jpeg(_jpeg_bytes(), at_s=2.0)
    source = PhoneSource(hub)
    t, frame = next(source.frames())
    assert t == 2.0 and frame.shape[2] == 3
