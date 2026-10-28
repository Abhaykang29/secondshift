"""Mock Transcriber - scenario-driven (spec section 11.2).

Returns the active scenario's scripted narration segments, so narration
alignment and fact extraction run end to end on mocks.
Depends on: providers.mock.scenario, domain.checkup.
"""

from secondshift.domain.checkup import NarrationSegment
from secondshift.providers.mock.scenario import default_scenario_name, load_scenario


class MockTranscriber:
    """Stand-in for Muse Voice Transcribe (speech-to-text only)."""

    def __init__(self, scenario_name: str | None = None) -> None:
        self.scenario_name = scenario_name or default_scenario_name()

    def transcribe(self, audio_path: str, language_hint: str | None) -> list[NarrationSegment]:
        """Return the scenario's scripted narration."""
        scenario = load_scenario(self.scenario_name)
        return [
            NarrationSegment(
                capture_id="",
                t_start=float(s["t_start"]),
                t_end=float(s["t_end"]),
                text=str(s["text"]),
                language=s.get("language"),
            )
            for s in scenario.get("narration", [])
        ]
