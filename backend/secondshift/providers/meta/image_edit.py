"""Meta Muse Image adapter + normalizer - Phase 7.

VERIFIED live 2026-10-28:
- POST /v1/images/edits with a JSON body {"model": "muse-image-1.0",
  "prompt": ..., "images": [{"image_url": <data URI>}]} returns
  data[0].b64_json (WebP bytes). (A singular "image" field is rejected;
  the API's own error message documents the "images" shape.)
- POST /v1/images/generations {"model", "prompt"} works the same way.
normalize_image_response accepts b64_json or a URL, as before.
Depends on: providers.base, providers.cost, providers.meta.transport.
"""

import base64
from typing import Any

from secondshift.providers.base import ImageRef


def normalize_image_response(payload: dict[str, Any]) -> bytes:
    """Extract image bytes from an image-edit response payload."""
    data = payload.get("data") or []
    if not data:
        raise ValueError(f"No data in image response: keys={list(payload)}")
    first = data[0]
    if first.get("b64_json"):
        return base64.b64decode(first["b64_json"])
    if first.get("url"):
        import httpx

        return httpx.get(first["url"], timeout=60.0).content
    raise ValueError(f"Unrecognized image response entry: keys={list(first)}")


class MetaImageEditor:
    """Real Muse Image client (Phase 7 plug-in)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def edit(self, image: ImageRef, mask_png: bytes, prompt: str) -> bytes:
        """Edit one image with Muse Image (verified JSON shape).

        mask_png is accepted for interface compatibility; the verified
        JSON edits shape has no mask field, so the edit is prompt-guided
        over the whole frame (the caller watermarks the result anyway).
        """
        from secondshift.providers.meta.text_vision import image_part
        from secondshift.providers.meta.transport import post_json

        part = image_part(image)
        body = {
            "model": "muse-image-1.0",
            "prompt": prompt,
            "images": [{"image_url": part["image_url"]["url"]}],
        }
        return normalize_image_response(post_json("/images/edits", body, explicit_key=self.api_key))
