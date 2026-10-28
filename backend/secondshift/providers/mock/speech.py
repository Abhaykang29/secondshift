"""Mock Transcriber.

Why: narration flows must work without Muse Voice Transcribe. The mock
returns scripted segments in Phase 1+; Phase 0 returns an empty list.
Depends on: providers.base, domain.checkup.
"""

from secondshift.domain.checkup import NarrationSegment


class MockTranscriber:
    """Stand-in for Muse Voice Transcribe (speech-to-text only)."""

    def transcribe(self, audio_path: str, language_hint: str | None) -> list[NarrationSegment]:
        """Phase 0: no scripted narration yet."""
        return []
