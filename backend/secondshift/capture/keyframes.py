"""Keyframe selection (spec section 9.2).

Goal: ~40-80 keyframes covering the home without duplicates. A frame is
kept when it is usable AND (it differs enough from the last kept frame OR
too much time has passed). The cap sub-samples uniformly.
Depends on: opencv, numpy, domain.checkup.Keyframe.
"""

from pathlib import Path

import cv2
import numpy as np

from secondshift.capture.quality import frame_metrics, is_usable
from secondshift.domain.checkup import Keyframe

_DESCR_SIZE = 32


def frame_descriptor(image: np.ndarray) -> np.ndarray:
    """Cheap descriptor: 32x32 grayscale, flattened and normalized."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    small = cv2.resize(gray, (_DESCR_SIZE, _DESCR_SIZE)).astype(np.float32) / 255.0
    return small.flatten()


def change_score(a: np.ndarray, b: np.ndarray) -> float:
    """Mean absolute difference between two descriptors (0 = identical)."""
    return float(np.abs(a - b).mean())


def select_keyframes(
    frame_paths: list[Path],
    capture_id: str,
    sample_fps: float,
    sharpness_min: float = 100.0,
    brightness_min: float = 30.0,
    brightness_max: float = 230.0,
    change_min: float = 0.015,
    max_gap_s: float = 3.0,
    max_keyframes: int = 80,
) -> list[Keyframe]:
    """Select keyframes from extracted frame files (in timestamp order)."""
    kept: list[Keyframe] = []
    last_descr: np.ndarray | None = None
    last_kept_t = -1e9
    for idx, path in enumerate(frame_paths):
        t = idx / sample_fps
        image = cv2.imread(str(path))
        if image is None:
            continue
        sharpness, brightness = frame_metrics(image)
        usable = is_usable(sharpness, brightness, sharpness_min, brightness_min, brightness_max)
        descr = frame_descriptor(image)
        changed = last_descr is None or change_score(descr, last_descr) > change_min
        gap = t - last_kept_t > max_gap_s
        if usable and (changed or gap):
            kept.append(
                Keyframe(
                    id=f"{capture_id}-kf-{len(kept):03d}",
                    capture_id=capture_id,
                    t=t,
                    image_path=str(path),
                    sharpness=sharpness,
                    brightness=brightness,
                    usable=True,
                )
            )
            last_descr = descr
            last_kept_t = t
    if len(kept) > max_keyframes:
        step = len(kept) / max_keyframes
        kept = [kept[int(i * step)] for i in range(max_keyframes)]
    return kept
