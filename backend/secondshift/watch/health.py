"""Camera health checks (spec section 9.14): dark, uniform, frozen, moved.

Pure functions on frames/descriptor history - unit-tested on synthetic
arrays. A health failure moves the rule to CANNOT_SEE and raises exactly
one "I can't see the stove" event per failure episode.
Depends on: numpy, opencv.
"""

import hashlib

import cv2
import numpy as np


def is_dark(frame: np.ndarray, threshold: float = 15.0) -> bool:
    """Mean grayscale below threshold = the camera sees darkness."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return float(gray.mean()) < threshold


def is_uniform(frame: np.ndarray, threshold: float = 2.0) -> bool:
    """Near-zero variance = covered lens or a blank wall."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return float(gray.std()) < threshold


def frame_hash(frame: np.ndarray) -> str:
    """A cheap content hash for frozen-frame detection."""
    small = cv2.resize(frame, (16, 16))
    return hashlib.sha256(small.tobytes()).hexdigest()


def is_frozen(hashes: list[str], min_identical: int = 30) -> bool:
    """True when the last min_identical frame hashes are all identical."""
    if len(hashes) < min_identical:
        return False
    return len(set(hashes[-min_identical:])) == 1


def descriptor(frame: np.ndarray) -> np.ndarray:
    """32x32 grayscale descriptor (same idea as keyframe selection)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return cv2.resize(gray, (32, 32)).astype(np.float32) / 255.0


def camera_moved(reference: np.ndarray, current: np.ndarray, threshold: float = 0.12) -> bool:
    """Mean absolute descriptor difference beyond threshold = moved."""
    return float(np.abs(reference - current).mean()) > threshold
