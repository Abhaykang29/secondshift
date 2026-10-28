"""Narration alignment and routine-fact extraction (spec section 9.3).

Segments are attached to keyframes/hazards within +/-5s as narration_notes.
Fact extraction drops health details by design: only space/routine facts
with known affect-tags survive the deterministic extractor used by mocks;
the real path uses prompts/narration_facts.md through the VisionReasoner.
Depends on: domain models, providers.base.Transcriber.
"""

import re

from secondshift.domain.checkup import Keyframe, NarrationFact, NarrationSegment
from secondshift.providers.base import Transcriber

_AFFECT_PATTERNS: list[tuple[str, list[str]]] = [
    (r"twice a night|at night|night", ["night_path"]),
    (r"bathroom", ["night_path", "bathroom"]),
    (r"stairs", ["stairs"]),
    (r"kitchen", ["kitchen"]),
    (r"holds|holding|grabs|support", ["routine_path"]),
]


def extract_facts(segments: list[NarrationSegment]) -> list[NarrationFact]:
    """Extract space/routine facts from narration segments (deterministic).

    Health words cause the whole sentence to be dropped, never stored.
    """
    facts: list[NarrationFact] = []
    health = re.compile(
        r"\b(diabetes|dementia|alzheimer|arthritis|cancer|diagnosed|medication|doctor said)\b", re.I
    )
    for segment in segments:
        for sentence in re.split(r"[.!]", segment.text):
            sentence = sentence.strip()
            if not sentence or health.search(sentence):
                continue
            affects: list[str] = []
            for pattern, tags in _AFFECT_PATTERNS:
                if re.search(pattern, sentence, re.I):
                    affects.extend(tags)
            if affects:
                facts.append(
                    NarrationFact(
                        fact=sentence,
                        t=segment.t_start,
                        affects=sorted(set(affects)),
                    )
                )
    return facts


def transcribe_capture(
    transcriber: Transcriber,
    audio_path: str | None,
    capture_id: str,
    language_hint: str | None,
) -> list[NarrationSegment]:
    """Transcribe a capture's audio (empty list when there is no audio)."""
    if audio_path is None:
        return []
    segments = transcriber.transcribe(audio_path, language_hint)
    return [s.model_copy(update={"capture_id": capture_id}) for s in segments]


def notes_near(segments: list[NarrationSegment], t: float, window_s: float = 5.0) -> list[str]:
    """Narration texts within +/- window of a timestamp."""
    return [s.text for s in segments if abs(s.t_start - t) <= window_s]


def keyframes_with_notes(
    keyframes: list[Keyframe], segments: list[NarrationSegment]
) -> dict[str, list[str]]:
    """Map keyframe id -> narration notes near it."""
    return {kf.id: notes_near(segments, kf.t) for kf in keyframes}
