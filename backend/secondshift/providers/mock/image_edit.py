"""Mock ImageEditor.

Why: visualizations must exist in the UI before Muse Image is wired.
The mock returns fixed placeholder PNG bytes; Phase 3 draws the labelled
overlay inside the mask region (spec section 11.2).
Depends on: providers.base.
"""

from secondshift.providers.base import ImageRef

# 1x1 transparent PNG.
_PLACEHOLDER_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000000020001e221bc33000000"
    "0049454e44ae426082"
)


class MockImageEditor:
    """Stand-in for Muse Image edits."""

    def edit(self, image: ImageRef, mask_png: bytes, prompt: str) -> bytes:
        """Return placeholder PNG bytes (Phase 3: labelled overlay)."""
        return _PLACEHOLDER_PNG
