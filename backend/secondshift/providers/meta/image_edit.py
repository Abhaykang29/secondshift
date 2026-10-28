"""Meta Muse Image adapter. Phase 7 only. TODO(API): verify multipart fields."""

from secondshift.providers.base import ImageRef
from secondshift.providers.cost import ProviderUnavailable


class MetaImageEditor:
    """Real Muse Image client - not yet wired (Phase 7)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def edit(self, image: ImageRef, mask_png: bytes, prompt: str) -> bytes:
        """TODO(API) Phase 7."""
        raise ProviderUnavailable("TODO(API): Muse Image adapter lands in Phase 7.")
