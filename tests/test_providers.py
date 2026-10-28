"""Provider skeleton tests: registry defaults to mock, mock is deterministic."""

from secondshift.config import Settings
from secondshift.domain.enums import ProviderName
from secondshift.providers.base import ImageRef
from secondshift.providers.mock.segmentation import MockSegmenter
from secondshift.providers.registry import build_providers


def test_registry_defaults_to_mock_providers() -> None:
    """With no env set, every role is the mock provider."""
    providers = build_providers(Settings())
    assert type(providers.vision).__name__ == "MockVisionReasoner"
    assert type(providers.segmenter).__name__ == "MockSegmenter"


def test_settings_default_provider_is_mock() -> None:
    """PROVIDER defaults to mock - the app works with no API keys."""
    assert Settings().provider is ProviderName.MOCK


def test_mock_segmenter_is_deterministic() -> None:
    """Same image + prompts -> identical masks, every time."""
    segmenter = MockSegmenter()
    image = ImageRef(path="frame.jpg", keyframe_id="k1")
    first = segmenter.segment(image, ["throw rug"])
    second = segmenter.segment(image, ["throw rug"])
    assert first == second
    assert first[0].prompt == "throw rug"
    assert first[0].score >= 0.5
