"""Mock ImageEditor (pass 2 Phase F.5).

The mock NEVER fakes an edit: it returns the input image stamped
"MOCK - no edit", so a mock-mode report can never be mistaken for a
real Muse Image result. Falls back to a 1x1 placeholder when the
input cannot be read (demo stubs).
Depends on: providers.base, PIL.
"""

import io

from PIL import Image, ImageDraw

from secondshift.providers.base import ImageRef

# 1x1 transparent PNG.
_PLACEHOLDER_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000000020001e221bc33000000"
    "0049454e44ae426082"
)


class MockImageEditor:
    """Returns the input stamped MOCK - no edit."""

    def edit(self, image: ImageRef, mask_png: bytes, prompt: str) -> bytes:
        """Stamp the input image; no edit is performed."""
        try:
            img = Image.open(image.path).convert("RGB")
        except Exception:
            return _PLACEHOLDER_PNG
        draw = ImageDraw.Draw(img)
        draw.text((8, 8), "MOCK - no edit", fill=(255, 220, 120))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
