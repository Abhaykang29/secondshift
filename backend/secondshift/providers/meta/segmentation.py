"""Meta SAM 3.1 adapter + response normalizer - Phase 7 plug-in.

The normalizer accepts the best-known response families (spec section
12.1): a "masks" or "results" list whose entries carry a polygon as
[[x,y],...] or a flat "points" list, a bbox, and a score under "score" or
"confidence". RLE masks (COCO-style counts) are detected and raise a
clear error: decoding them is a runbook fix once the real format is seen.
TODO(API) on every shape assumption.
Depends on: providers.base, domain.hazards.
"""

from typing import Any

from secondshift.domain.hazards import Mask
from secondshift.providers.base import ImageRef
from secondshift.providers.cost import ProviderUnavailable


def _polygon_from(entry: dict[str, Any]) -> list[tuple[float, float]] | None:
    poly = entry.get("polygon") or entry.get("points")
    if isinstance(poly, list) and poly and isinstance(poly[0], (int, float)):
        flat = [float(v) for v in poly]
        return [(flat[i], flat[i + 1]) for i in range(0, len(flat) - 1, 2)]
    if isinstance(poly, list):
        return [(float(x), float(y)) for x, y in poly]
    return None


def _bbox(
    poly: list[tuple[float, float]] | None, entry: dict[str, Any]
) -> tuple[float, float, float, float]:
    raw = entry.get("bbox") or entry.get("box")
    if isinstance(raw, list) and len(raw) == 4:
        return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    if poly:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        return (min(xs), min(ys), max(xs), max(ys))
    return (0.0, 0.0, 0.0, 0.0)


def normalize_sam_response(
    payload: dict[str, Any], keyframe_id: str, default_prompt: str = ""
) -> list[Mask]:
    """Normalize a SAM response payload into our Mask list.

    Raises ValueError on RLE-only payloads (TODO(API): decode once the
    real format is confirmed) and on unrecognized shapes.
    """
    raw_masks = payload.get("masks") or payload.get("results") or payload.get("segments")
    if raw_masks is None:
        raise ValueError(f"Unrecognized SAM response: keys={list(payload)}")
    masks: list[Mask] = []
    for entry in raw_masks:
        if isinstance(entry.get("segmentation"), dict) and "counts" in entry["segmentation"]:
            raise ValueError("TODO(API): RLE mask received - decode step goes here.")
        poly = _polygon_from(entry)
        score = entry.get("score", entry.get("confidence", 0.0))
        masks.append(
            Mask(
                keyframe_id=keyframe_id,
                polygon=poly,
                bbox=_bbox(poly, entry),
                score=float(score),
                prompt=str(entry.get("label", entry.get("prompt", default_prompt))),
            )
        )
    return masks


class MetaSegmenter:
    """Real SAM 3.1 client (Phase 7 plug-in)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        """TODO(API): endpoint, image upload format, prompt field names."""
        if not self.api_key:
            raise ProviderUnavailable("META_API_KEY is not set - SAM adapter is off.")
        raise ProviderUnavailable(
            "TODO(API): SAM endpoint call lands here; normalize_sam_response is ready and tested."
        )

    def segment_video(self, frames: list[ImageRef], prompts: list[str]) -> dict[str, list[Mask]]:
        """Per-frame fallback unless the API exposes video tracking (TODO(API))."""
        return {
            (f.keyframe_id or f"frame-{i}"): self.segment(f, prompts) for i, f in enumerate(frames)
        }
