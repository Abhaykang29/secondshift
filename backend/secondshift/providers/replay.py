"""Record/replay provider wrappers (spec sections 11.3 / 16 Phase 8).

RecordingVision wraps any VisionReasoner and stores each propose
response in the RecordReplayCache under a scenario key; ReplayVision
answers ONLY from the cache - a miss raises CacheMiss, so a demo in
replay mode can never silently call a live (or mock-live) provider.
Same pattern for the segmenter (per-prompt-set) and transcriber.
Depends on: providers.base, providers.cache, domain models.
"""

from typing import Any

from secondshift.domain.checkup import NarrationSegment
from secondshift.domain.hazards import HazardProposal, Mask
from secondshift.providers.base import (
    ImageRef,
    JudgeRequest,
    JudgeResponse,
    ProposeRequest,
    ProposeResponse,
    Segmenter,
    Transcriber,
    VisionReasoner,
)
from secondshift.providers.cache import RecordReplayCache, cache_key


def _propose_key(scenario: str) -> str:
    return cache_key("recorded", "vision", "propose", {"scenario": scenario}, [])


def _segment_key(scenario: str, prompts: list[str]) -> str:
    return cache_key(
        "recorded", "sam", "segment", {"scenario": scenario, "prompts": sorted(prompts)}, []
    )


class RecordingVision:
    """Wraps a VisionReasoner, recording propose responses to the cache."""

    def __init__(self, inner: VisionReasoner, cache: RecordReplayCache, scenario: str) -> None:
        self.inner = inner
        self.cache = cache
        self.scenario_name = scenario

    def propose_hazards(self, req: ProposeRequest) -> ProposeResponse:
        """Call through and record the serialized response."""
        response = self.inner.propose_hazards(req)
        payload = {
            "proposals": [p.model_dump(mode="json") for p in response.proposals],
            "rooms_seen": response.rooms_seen,
            "keyframe_rooms": response.keyframe_rooms,
            "cannot_assess": [c.model_dump(mode="json") for c in response.cannot_assess],
        }
        self.cache.put(_propose_key(self.scenario_name), payload, model="recorded")
        return response

    def judge(self, req: JudgeRequest) -> JudgeResponse:
        """Judging delegates (judge calls are part of scan determinism via mocks)."""
        return self.inner.judge(req)

    def complete_json(
        self, prompt: str, images: list[ImageRef], schema: Any, model_role: Any
    ) -> Any:
        """Delegates - structured calls are not part of the demo recording."""
        return self.inner.complete_json(prompt, images, schema, model_role)

    # Pass 2 E/G protocol methods delegate to the inner provider.
    def plan_fix(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Delegate."""
        return self.inner.plan_fix(*args, **kwargs)

    def summarize_report(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Delegate."""
        return self.inner.summarize_report(*args, **kwargs)

    def judge_recheck(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Delegate."""
        return self.inner.judge_recheck(*args, **kwargs)

    def plan_edit(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Delegate."""
        return self.inner.plan_edit(*args, **kwargs)

    def routine_insights(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Delegate."""
        return self.inner.routine_insights(*args, **kwargs)

    def classify_room(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Delegate."""
        return self.inner.classify_room(*args, **kwargs)

    def judge_state(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Delegate."""
        return self.inner.judge_state(*args, **kwargs)

    def compile_rule(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Delegate."""
        return self.inner.compile_rule(*args, **kwargs)


class ReplayVision:
    """Answers propose calls from the cache only. Miss = CacheMiss."""

    # Pass 2 E/G: replay has no opinions - deterministic paths reproduce
    # the recorded demo exactly.
    def plan_fix(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """No opinion in replay."""
        return None

    def summarize_report(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """No opinion in replay."""
        return None

    def judge_recheck(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """No opinion in replay."""
        return None

    def plan_edit(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """No opinion in replay."""
        return None

    def routine_insights(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """No opinion in replay."""
        return None

    def classify_room(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """No opinion in replay."""
        return None

    def judge_state(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """No opinion in replay."""
        return None

    def compile_rule(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Rules are not compiled in replay."""
        return None

    def __init__(self, cache: RecordReplayCache, scenario: str) -> None:
        self.cache = cache
        self.scenario_name = scenario

    def propose_hazards(self, req: ProposeRequest) -> ProposeResponse:
        """Return the recorded propose response for the scenario."""
        got = self.cache.get(_propose_key(self.scenario_name))
        assert got is not None  # get() raises CacheMiss in replay mode
        payload = got["response"]
        return ProposeResponse(
            proposals=[HazardProposal.model_validate(p) for p in payload["proposals"]],
            rooms_seen=list(payload["rooms_seen"]),
            keyframe_rooms=list(payload.get("keyframe_rooms", [])),
            cannot_assess=[],
        )

    def judge(self, req: JudgeRequest) -> JudgeResponse:
        """Deterministic replay judge (matches the mock judge's contract)."""
        if "sam_found: false" in req.context:
            return JudgeResponse(
                verification="rejected",
                reason="SAM found no matching object in the evidence frames.",
            )
        if "state_check" in req.context:
            return JudgeResponse(
                verification="confirmed", reason="Mock judge: the visible state matches the claim."
            )
        return JudgeResponse(verification="needs_human", reason="Mock judge: human review.")

    def complete_json(
        self, prompt: str, images: list[ImageRef], schema: Any, model_role: Any
    ) -> Any:
        """Not available in replay mode."""
        raise NotImplementedError("complete_json is not recorded for replay.")


class RecordingSegmenter:
    """Wraps a Segmenter, recording masks per (scenario, prompt set)."""

    def __init__(self, inner: Segmenter, cache: RecordReplayCache, scenario: str) -> None:
        self.inner = inner
        self.cache = cache
        self.scenario_name = scenario

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        """Call through and record."""
        masks = self.inner.segment(image, prompts)
        self.cache.put(
            _segment_key(self.scenario_name, prompts),
            {"masks": [m.model_dump(mode="json") for m in masks]},
            model="recorded",
        )
        return masks

    def segment_video(self, frames: list[ImageRef], prompts: list[str]) -> dict[str, list[Mask]]:
        """Per-frame via segment()."""
        return {
            (f.keyframe_id or f"frame-{i}"): self.segment(f, prompts) for i, f in enumerate(frames)
        }


class ReplaySegmenter:
    """Answers segment calls from the cache only (keyframe id re-stamped)."""

    def __init__(self, cache: RecordReplayCache, scenario: str) -> None:
        self.cache = cache
        self.scenario_name = scenario

    def segment(self, image: ImageRef, prompts: list[str]) -> list[Mask]:
        """Return recorded masks for this prompt set, stamped for this frame."""
        got = self.cache.get(_segment_key(self.scenario_name, prompts))
        assert got is not None
        masks = [Mask.model_validate(m) for m in got["response"]["masks"]]
        for mask in masks:
            mask.keyframe_id = image.keyframe_id or mask.keyframe_id
        return masks

    def segment_video(self, frames: list[ImageRef], prompts: list[str]) -> dict[str, list[Mask]]:
        """Per-frame via segment()."""
        return {
            (f.keyframe_id or f"frame-{i}"): self.segment(f, prompts) for i, f in enumerate(frames)
        }


class RecordingTranscriber:
    """Wraps a Transcriber, recording its segments."""

    def __init__(self, inner: Transcriber, cache: RecordReplayCache, scenario: str) -> None:
        self.inner = inner
        self.cache = cache
        self.scenario_name = scenario

    def transcribe(self, audio_path: str, language_hint: str | None) -> list[NarrationSegment]:
        """Call through and record."""
        segments = self.inner.transcribe(audio_path, language_hint)
        self.cache.put(
            cache_key("recorded", "transcribe", "segments", {"scenario": self.scenario_name}, []),
            {"segments": [s.model_dump(mode="json") for s in segments]},
            model="recorded",
        )
        return segments


class ReplayTranscriber:
    """Answers transcription from the cache only."""

    def __init__(self, cache: RecordReplayCache, scenario: str) -> None:
        self.cache = cache
        self.scenario_name = scenario

    def transcribe(self, audio_path: str, language_hint: str | None) -> list[NarrationSegment]:
        """Return the recorded segments for the scenario."""
        got = self.cache.get(
            cache_key("recorded", "transcribe", "segments", {"scenario": self.scenario_name}, [])
        )
        assert got is not None
        return [NarrationSegment.model_validate(s) for s in got["response"]["segments"]]
