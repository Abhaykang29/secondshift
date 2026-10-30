"""Person blurring (spec 14.3, pass 2 Phase E).

Every frame we write to disk (keyframes, evidence, report images, watch
thumbnails) must have people blurred BEFORE it is saved. We ask SAM for
"person" boxes on the frame and Gaussian-blur those regions in place.

Failure policy (honest and safe): if the SAM call fails, the caller
gets blurred=False and decides - report/evidence writers must then use
blur_all_but() so an unblurred person is never saved by accident.
Results are cached per (path, mtime) so re-processing a scan is cheap.
Depends on: providers.base (Segmenter), opencv.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from secondshift.providers.base import ImageRef, Segmenter

logger = logging.getLogger(__name__)

_cache: dict[tuple[str, float], int] = {}
_cache_lock = threading.Lock()


def _blur_region(frame: np.ndarray, bbox: tuple[float, ...]) -> None:
    """Gaussian-blur one normalized bbox region in place."""
    height, width = frame.shape[:2]
    x0, y0 = int(bbox[0] * width), int(bbox[1] * height)
    x1, y1 = int(bbox[2] * width), int(bbox[3] * height)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(width, x1), min(height, y1)
    if x1 <= x0 or y1 <= y0:
        return
    roi = frame[y0:y1, x0:x1]
    # Kernel scaled to ~51px at 1080p, always odd.
    k = max(3, int(51 * height / 1080) | 1)
    frame[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (k, k), 0)


def blur_persons(image_path: str, segmenter: Segmenter) -> int:
    """Blur every person SAM finds in the image at image_path, in place.

    Returns the number of person regions blurred. Raises nothing: on a
    provider failure it returns -1 so the caller can fall back to
    blur_all_but() instead of saving an unblurred frame.
    """
    path = Path(image_path)
    if not path.exists():
        return -1
    key = (str(path), path.stat().st_mtime)
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    frame = cv2.imread(str(path))
    if frame is None:
        return -1
    ref = ImageRef(path=str(path), keyframe_id=path.stem)
    try:
        masks = segmenter.segment(ref, ["person"])
    except Exception:
        logger.warning("person segmentation failed for %s", path.name)
        return -1
    for mask in masks:
        _blur_region(frame, mask.bbox)
    if masks:
        cv2.imwrite(str(path), frame)
    with _cache_lock:
        _cache[key] = len(masks)
    return len(masks)


def blur_keyframes(image_paths: list[str], segmenter: Segmenter, max_workers: int = 8) -> list[int]:
    """Blur persons in many keyframes in parallel (smoke-test fix 8).

    Order-preserving; each frame's SAM call still goes through the
    transport's per-model throttle. Returns blur_persons' per-frame
    results (count blurred, or -1 on failure).
    """
    if not image_paths:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(image_paths))) as pool:
        return list(pool.map(lambda p: blur_persons(p, segmenter), image_paths))


def blur_all_but(image_path: str, keep_bbox: tuple[float, ...] | None) -> bool:
    """Fallback: blur the WHOLE frame except keep_bbox (the hazard box).

    Used when person segmentation failed: a mostly-blurred evidence
    image is honest; an unblurred person is a privacy incident.
    """
    path = Path(image_path)
    frame = cv2.imread(str(path))
    if frame is None:
        return False
    height, width = frame.shape[:2]
    k = max(3, int(51 * height / 1080) | 1)
    blurred = cv2.GaussianBlur(frame, (k, k), 0)
    if keep_bbox is not None:
        x0, y0 = int(keep_bbox[0] * width), int(keep_bbox[1] * height)
        x1, y1 = int(keep_bbox[2] * width), int(keep_bbox[3] * height)
        blurred[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)] = frame[
            max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)
        ]
    cv2.imwrite(str(path), blurred)
    return True
