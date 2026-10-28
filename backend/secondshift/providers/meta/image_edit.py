"""Meta Muse Image adapter + normalizer - Phase 7 plug-in.

Best-known shape (spec section 12.1): an images/edits-style call
returning data[0].b64_json (or a URL). Both are normalized to PNG bytes
by normalize_image_response. TODO(API) on endpoint + multipart fields.
Depends on: providers.base, providers.cost.
"""

import base64
from typing import Any

from secondshift.providers.base import ImageRef
from secondshift.providers.cost import ProviderUnavailable


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
        """TODO(API): multipart field names for image + mask + prompt."""
        if not self.api_key:
            raise ProviderUnavailable("META_API_KEY is not set - Muse Image adapter is off.")
        raise ProviderUnavailable(
            "TODO(API): Muse Image edit call lands here; normalize_image_response is ready."
        )
