"""Meta Muse Voice Transcribe adapter. Phase 7 only. TODO(API)."""

from secondshift.domain.checkup import NarrationSegment
from secondshift.providers.cost import ProviderUnavailable


class MetaTranscriber:
    """Real transcription client - not yet wired (Phase 7)."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def transcribe(self, audio_path: str, language_hint: str | None) -> list[NarrationSegment]:
        """TODO(API) Phase 7."""
        raise ProviderUnavailable("TODO(API): Transcribe adapter lands in Phase 7.")
