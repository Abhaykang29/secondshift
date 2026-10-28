"""Meta SAM 3.1 adapter. Phase 7 only. TODO(API): endpoint/format unknown.

The adapter must normalize polygon / RLE / PNG-mask responses into our Mask.
Depends on: providers.base.
"""

from secondshift.domain.hazards import Mask
from secondshift.providers.base import ImageRef
from secondshift.providers.cost import ProviderUnavailable


class MetaSegmenter:
    """Real SAM 3.1 client - not yet wired (Phase 7)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        """TODO(API) Phase 7."""
        raise ProviderUnavailable("TODO(API): SAM adapter lands in Phase 7.")

    def segment_video(self, frames: list[ImageRef], prompts: list[str]) -> dict[str, list[Mask]]:
        """TODO(API) Phase 7: video tracking if exposed, else per-frame."""
        raise ProviderUnavailable("TODO(API): SAM adapter lands in Phase 7.")
