"""Mock Segmenter.

Why: verification logic needs masks to test against. The mock returns one
deterministic, plausible mask per prompt so pipeline code can be exercised
without SAM. Phase 2 replaces the box geometry with scenario polygons.
Depends on: providers.base, domain.hazards.Mask.
"""

from secondshift.domain.hazards import Mask
from secondshift.providers.base import ImageRef


class MockSegmenter:
    """Deterministic stand-in for SAM 3.1."""

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        """Return one centred mask per prompt, keyed to the image ref."""
        keyframe_id = image.keyframe_id or "unknown"
        return [
            Mask(
                keyframe_id=keyframe_id,
                polygon=[(0.30, 0.60), (0.70, 0.60), (0.70, 0.95), (0.30, 0.95)],
                bbox=(0.30, 0.60, 0.70, 0.95),
                score=0.90,
                prompt=prompt,
            )
            for prompt in prompts
        ]

    def segment_video(self, frames: list[ImageRef], prompts: list[str]) -> dict[str, list[Mask]]:
        """Per-frame fallback, keyed by keyframe id."""
        return {
            (frame.keyframe_id or f"frame-{i}"): self.segment(frame, prompts)
            for i, frame in enumerate(frames)
        }
