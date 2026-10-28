"""Mock Segmenter - scenario-driven (spec section 11.2).

Returns the scenario-authored polygon for a prompt, and - critically -
returns NOTHING for prompts the scenario says are absent (safety objects
with safety_found=false, and segment_missing false positives). That is
what makes SAM verification meaningful on mocks.
Depends on: providers.base, providers.mock.scenario, domain.hazards.
"""

from secondshift.domain.hazards import Mask
from secondshift.providers.base import ImageRef
from secondshift.providers.mock.scenario import (
    default_scenario_name,
    load_scenario,
    missing_prompts,
    polygon_for,
)

_DEFAULT_POLY: list[tuple[float, float]] = [(0.30, 0.60), (0.70, 0.60), (0.70, 0.95), (0.30, 0.95)]


def _bbox(poly: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return (min(xs), min(ys), max(xs), max(ys))


class MockSegmenter:
    """Deterministic stand-in for SAM 3.1."""

    def __init__(self, scenario_name: str | None = None) -> None:
        self.scenario_name = scenario_name or default_scenario_name()

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        """One mask per found prompt; absent prompts return no mask."""
        scenario = load_scenario(self.scenario_name)
        missing = missing_prompts(scenario)
        masks: list[Mask] = []
        for prompt in prompts:
            if prompt in missing:
                continue
            poly = polygon_for(scenario, prompt) or _DEFAULT_POLY
            masks.append(
                Mask(
                    keyframe_id=image.keyframe_id or "unknown",
                    polygon=poly,
                    bbox=_bbox(poly),
                    score=0.90,
                    prompt=prompt,
                )
            )
        return masks

    def segment_video(self, frames: list[ImageRef], prompts: list[str]) -> dict[str, list[Mask]]:
        """Per-frame fallback, keyed by keyframe id."""
        return {
            (frame.keyframe_id or f"frame-{i}"): self.segment(frame, prompts)
            for i, frame in enumerate(frames)
        }
