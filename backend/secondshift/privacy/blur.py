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

import hashlib
import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from secondshift.providers.base import ImageRef, Segmenter

logger = logging.getLogger(__name__)

_cache: dict[tuple[str, float], int] = {}
_cache_lock = threading.Lock()

# Persistent person-box cache (consistency pass, 2026-11-03): SAM's
# boxes for a frame are stored under the sha256 of the frame's
# pristine bytes, so a re-upload of the same video blurs the exact
# same regions without a new SAM call - blur is identical across
# runs. (A re-scan of an already-blurred capture hashes the blurred
# bytes and misses; fresh uploads are the identical-blur path.)
_box_cache: dict[str, list[list[float]]] | None = None
_box_cache_lock = threading.Lock()


def _box_cache_path() -> Path:
    return Path(os.environ.get("DATA_DIR", "data")) / "blur_boxes.json"


def _load_box_cache() -> dict[str, list[list[float]]]:
    global _box_cache
    if _box_cache is None:
        try:
            _box_cache = json.loads(_box_cache_path().read_text())
        except (OSError, ValueError):
            _box_cache = {}
    return _box_cache


def _cache_key(frame_sha: str, segmenter: Segmenter) -> str:
    """Cache entries are per segmenter: a stub's boxes must never be
    served to the real provider or vice versa (a shared key once let
    a demo run's cached boxes mask a provider failure in a test)."""
    return f"{frame_sha}:{type(segmenter).__module__}.{type(segmenter).__name__}"


def _cached_boxes(frame_sha: str, segmenter: Segmenter) -> list[list[float]] | None:
    with _box_cache_lock:
        return _load_box_cache().get(_cache_key(frame_sha, segmenter))


def _store_boxes(frame_sha: str, segmenter: Segmenter, boxes: list[list[float]]) -> None:
    with _box_cache_lock:
        cache = _load_box_cache()
        cache[_cache_key(frame_sha, segmenter)] = boxes
        try:
            path = _box_cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cache))
        except OSError:
            logger.warning("could not persist the blur box cache")


def _write_atomic(path: Path, frame: np.ndarray) -> None:
    """Write a JPEG via a unique temp file + atomic rename, so a
    concurrent reader (the sweep crops frames while visualizations
    re-blur them) never sees a half-written file. A direct imwrite
    truncated the file mid-read and intermittently failed scans
    with PIL's UnidentifiedImageError (2026-11-03)."""
    suffix = path.suffix or ".jpg"
    tmp = path.with_name(f".{path.stem}-{uuid.uuid4().hex[:8]}.tmp{suffix}")
    cv2.imwrite(str(tmp), frame)
    os.replace(tmp, path)


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
    frame_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    cached = _cached_boxes(frame_sha, segmenter)
    if cached is not None:
        boxes: list[tuple[float, ...]] = [tuple(b) for b in cached]
    else:
        ref = ImageRef(path=str(path), keyframe_id=path.stem)
        try:
            masks = segmenter.segment(ref, ["person"])
        except Exception:
            logger.warning("person segmentation failed for %s", path.name)
            return -1
        boxes = [tuple(m.bbox) for m in masks]
        _store_boxes(frame_sha, segmenter, [list(b) for b in boxes])
    for bbox in boxes:
        _blur_region(frame, bbox)
    if boxes:
        _write_atomic(path, frame)
    with _cache_lock:
        _cache[key] = len(boxes)
    return len(boxes)


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
    _write_atomic(path, blurred)
    return True
