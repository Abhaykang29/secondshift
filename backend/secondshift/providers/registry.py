"""Provider registry: builds provider implementations from config.

Why: exactly one place decides mock vs meta vs local, including per-role
overrides (e.g. SEGMENTER=mock while vision is real). Spec section 11.1.
Depends on: config.Settings, provider implementations.
"""

from dataclasses import dataclass

from secondshift.config import Settings
from secondshift.domain.enums import ProviderName
from secondshift.providers.base import (
    ImageEditor,
    Segmenter,
    Transcriber,
    VisionReasoner,
)
from secondshift.providers.cache import RecordReplayCache
from secondshift.providers.cost import CostGuard
from secondshift.providers.meta.image_edit import MetaImageEditor
from secondshift.providers.meta.segmentation import MetaSegmenter
from secondshift.providers.meta.speech import MetaTranscriber
from secondshift.providers.meta.text_vision import MetaVisionReasoner
from secondshift.providers.mock.image_edit import MockImageEditor
from secondshift.providers.mock.segmentation import MockSegmenter
from secondshift.providers.mock.speech import MockTranscriber
from secondshift.providers.mock.vision import MockVisionReasoner


@dataclass
class Providers:
    """The four provider roles plus shared cache and cost guard."""

    vision: VisionReasoner
    segmenter: Segmenter
    image_editor: ImageEditor
    transcriber: Transcriber
    cache: RecordReplayCache
    cost: CostGuard


def build_providers(settings: Settings) -> Providers:
    """Build all providers for the given settings.

    Example: ``build_providers(Settings()).vision`` is a MockVisionReasoner
    under the default mock configuration.
    """
    vision_name = settings.vision_override or settings.provider
    segmenter_name = settings.segmenter_override or settings.provider

    vision: VisionReasoner
    if vision_name is ProviderName.META:
        vision = MetaVisionReasoner(settings.meta_api_key)
    else:
        vision = MockVisionReasoner()  # LOCAL is a stretch goal (spec 19.3)

    segmenter: Segmenter
    if segmenter_name is ProviderName.META:
        segmenter = MetaSegmenter(settings.meta_api_key)
    else:
        segmenter = MockSegmenter()

    image_editor: ImageEditor = (
        MetaImageEditor(settings.meta_api_key)
        if settings.provider is ProviderName.META
        else MockImageEditor()
    )
    transcriber: Transcriber = (
        MetaTranscriber(settings.meta_api_key)
        if settings.provider is ProviderName.META
        else MockTranscriber()
    )
    return Providers(
        vision=vision,
        segmenter=segmenter,
        image_editor=image_editor,
        transcriber=transcriber,
        cache=RecordReplayCache(settings.cache_dir, settings.cache_mode),
        cost=CostGuard(
            budget_usd=settings.budget_usd,
            override=settings.budget_override,
            image_tokens_estimate=settings.image_tokens_estimate,
        ),
    )
