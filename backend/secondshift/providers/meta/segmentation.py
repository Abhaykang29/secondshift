"""Meta SAM 3.1 adapter + response normalizers - Phase 7.

VERIFIED live 2026-10-28: SAM 3.1 is served on POST /v1/responses
(it is NOT on /v1/chat/completions - the API says so itself). Request:
{"model": "sam-3.1", "input": [{"role": "user", "content":
[{"type": "input_text", "text": <prompt>},
 {"type": "input_image", "image_url": <data URI>}]}]}.
The reply's output text carries one segment per found object:
    <|box;x1=500;y1=200;x2=800;y2=600;w=1280;h=720|><|mask;x=0;y=0;data=...|>
Box coordinates are pixels in the w x h image; on the probe image the
box matched the drawn object EXACTLY. usage reports images_processed
(billed per image, tokens 0). No confidence score is returned, so masks
carry score=SAM_BOX_SCORE (documented constant, not a measurement).
The pixel mask payload uses a proprietary string encoding; v1 uses the
exact boxes for verification geometry and overlays. Decoding the pixel
masks is future work (PROGRESS.md TODO(TEAM)-adjacent note).
The legacy masks/results normalizer is kept for fixture compatibility.
Depends on: providers.base, domain.hazards, providers.meta.transport.
"""

import re
from typing import Any

from secondshift.domain.hazards import Mask
from secondshift.providers.base import ImageRef


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


BOX_RE = re.compile(
    r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>"
)

# SAM responses carry no confidence; boxes were pixel-exact on probes.
SAM_BOX_SCORE = 0.9


def parse_sam_responses_text(text: str, keyframe_id: str, prompt: str) -> list[Mask]:
    """Parse the verified SAM /v1/responses output text into Masks.

    One Mask per <|box;...|> segment, with normalized (0..1) polygon and
    bbox derived from the pixel box and the image size it declares.
    """
    masks: list[Mask] = []
    for match in BOX_RE.finditer(text):
        x1, y1, x2, y2, w, h = (int(g) for g in match.groups())
        if w <= 0 or h <= 0:
            continue
        nx1, ny1, nx2, ny2 = x1 / w, y1 / h, x2 / w, y2 / h
        masks.append(
            Mask(
                keyframe_id=keyframe_id,
                polygon=[(nx1, ny1), (nx2, ny1), (nx2, ny2), (nx1, ny2)],
                bbox=(nx1, ny1, nx2, ny2),
                score=SAM_BOX_SCORE,
                prompt=prompt,
            )
        )
    return masks


def normalize_sam_responses(payload: dict[str, Any], keyframe_id: str, prompt: str) -> list[Mask]:
    """Extract masks from a /v1/responses payload (verified shape)."""
    texts: list[str] = []
    for item in payload.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                texts.append(str(part.get("text", "")))
    return parse_sam_responses_text("\n".join(texts), keyframe_id, prompt)


class MetaSegmenter:
    """Real SAM 3.1 client (Phase 7 plug-in)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        """Segment via SAM 3.1 on /v1/responses (verified 2026-10-28).

        One call per text prompt (each call bills one image processed).
        """
        from secondshift.providers.meta.text_vision import image_part
        from secondshift.providers.meta.transport import post_json

        part = image_part(image)
        masks: list[Mask] = []
        for prompt in prompts:
            body = {
                "model": "sam-3.1",
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": part["image_url"]["url"]},
                        ],
                    }
                ],
            }
            payload = post_json("/responses", body, explicit_key=self.api_key)
            masks.extend(
                normalize_sam_responses(payload, image.keyframe_id or "", prompt)
            )
        return masks

    def segment_video(self, frames: list[ImageRef], prompts: list[str]) -> dict[str, list[Mask]]:
        """Per-frame fallback unless the API exposes video tracking (TODO(API))."""
        return {
            (f.keyframe_id or f"frame-{i}"): self.segment(f, prompts) for i, f in enumerate(frames)
        }
