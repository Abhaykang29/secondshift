"""Meta Muse Voice Transcribe adapter + normalizer - Phase 7 plug-in.

Best-known shape: segments with start/end (or offset/duration) + text +
language. normalize_transcript handles both families. Transcribe is
speech-to-text ONLY - there is no speaker identification (spec 12.1).
Depends on: domain.checkup, providers.cost.
"""

from typing import Any

from secondshift.domain.checkup import NarrationSegment
from secondshift.providers.cost import ProviderUnavailable


def normalize_transcript(payload: dict[str, Any], capture_id: str = "") -> list[NarrationSegment]:
    """Normalize a transcription payload into NarrationSegments."""
    raw = payload.get("segments")
    if raw is None and isinstance(payload.get("text"), str):
        return [
            NarrationSegment(
                capture_id=capture_id,
                t_start=0.0,
                t_end=float(payload.get("duration", 0.0)),
                text=payload["text"],
                language=payload.get("language"),
            )
        ]
    if raw is None:
        raise ValueError(f"Unrecognized transcript payload: keys={list(payload)}")
    segments: list[NarrationSegment] = []
    for entry in raw:
        start = float(entry.get("start", entry.get("t_start", 0.0)))
        if "end" in entry or "t_end" in entry:
            end = float(entry.get("end", entry.get("t_end", start)))
        else:
            end = start + float(entry.get("duration", 0.0))
        segments.append(
            NarrationSegment(
                capture_id=capture_id,
                t_start=start,
                t_end=end,
                text=str(entry.get("text", "")),
                language=entry.get("language", payload.get("language")),
            )
        )
    return segments


class MetaTranscriber:
    """Real transcription client (Phase 7 plug-in)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def transcribe(self, audio_path: str, language_hint: str | None) -> list[NarrationSegment]:
        """Transcribe via Muse Voice - endpoint NOT yet located (2026-10-28).

        Probes against the live API: POST /v1/audio/transcriptions
        (multipart and JSON) -> 404; the model is not served on
        /v1/chat/completions or /v1/responses (model_not_found). The
        model exists (GET /v1/models lists it). Until the route is
        found, this raises ProviderUnavailable and callers proceed
        without narration - the scan never depends on a transcript.
        normalize_transcript stays ready for the real payload.
        """
        raise ProviderUnavailable(
            "Muse Voice Transcribe endpoint not yet located "
            "(probed 2026-10-28: audio/transcriptions 404, chat/responses model_not_found)."
        )
