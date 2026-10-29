"""Configuration for SecondShift.

Why: spec section 17 rule 7 - config lives in exactly one place. Every
threshold, price and provider choice is read from the environment here;
no other module reads os.environ.
Depends on: domain.enums only.
"""

import os
from dataclasses import dataclass, field

from secondshift.domain.enums import CacheMode, ProviderName


def _f(name: str, default: float) -> float:
    """Read a float env var, falling back to the documented default."""
    raw = os.environ.get(name)
    return float(raw) if raw not in (None, "") else default


def _i(name: str, default: int) -> int:
    """Read an int env var, falling back to the documented default."""
    raw = os.environ.get(name)
    return int(raw) if raw not in (None, "") else default


# Best-known Meta prices (USD). TODO(API): verify in Phase 7 (spec section 11.4).
PRICE_TABLE: dict[str, dict[str, float]] = {
    "muse-spark-1.3": {"input_per_m": 1.25, "output_per_m": 4.25, "cached_input_per_m": 0.15},
    "muse-wonder-1.0": {"input_per_m": 4.00, "output_per_m": 20.00, "cached_input_per_m": 0.20},
    "muse-image-1.0": {"per_image": 0.01},
    "muse-voice-transcribe-1.0": {"per_audio_hour": 0.18},
    "sam-3.1": {"per_1000_images": 2.50, "per_1000_video_frames": 0.20},
}

MODEL_IDS: dict[str, str] = {
    "fast": "muse-spark-1.3",  # Standard tier only - never *-contributor (spec section 6)
    "deep": "muse-wonder-1.0",
    "segment": "sam-3.1",
    "image": "muse-image-1.0",
    "speech": "muse-voice-transcribe-1.0",
}


def _load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader: KEY=VALUE lines, never overriding real env."""
    from pathlib import Path as _P

    env_file = _P(path)
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class Settings:
    """All runtime settings, populated from the environment by ``load``."""

    provider: ProviderName = ProviderName.MOCK
    segmenter_override: ProviderName | None = None
    vision_override: ProviderName | None = None
    cache_mode: CacheMode = CacheMode.OFF
    cache_dir: str = "fixtures/recordings"
    budget_usd: float = 100.0
    budget_override: bool = False
    meta_api_key: str | None = None
    data_dir: str = "data"
    # Capture (spec section 9.1-9.2)
    max_capture_minutes: float = 6.0
    sample_fps: float = 2.0
    sharpness_min: float = 100.0
    brightness_min: float = 30.0
    brightness_max: float = 230.0
    scene_change_min: float = 0.25
    max_gap_s: float = 3.0
    max_keyframes: int = 80
    # Pipeline (spec sections 9.4-9.5)
    propose_batch: int = 12
    propose_model: str = "spark"
    verify_frames: int = 3
    min_mask_score: float = 0.5
    verify_mode: str = "sam_plus_judge"  # none | sam | sam_plus_judge
    image_tokens_estimate: int = 1200  # measured 2026-10-28
    routine_send_unblurred: bool = False
    # Watch (spec section 9.14)
    watch_fps: float = 1.0
    max_calls_per_hour: int = 60
    confirm_every_s: float = 60.0
    change_min: float = 0.02
    dark_max: float = 15.0
    uniform_std_max: float = 5.0
    move_min_match: float = 0.30
    # Privacy / eval flags
    allow_contributor_for_synthetic_text: bool = False
    retention_days: int = 30
    credits_mode: str = "free"  # free | paid - drives the privacy copy (see PRIVACY.md)
    watch_thumbnail_retention_days: int = 7
    price_table: dict[str, dict[str, float]] = field(default_factory=lambda: PRICE_TABLE)
    model_ids: dict[str, str] = field(default_factory=lambda: MODEL_IDS)

    @classmethod
    def load(cls) -> "Settings":
        """Build Settings from environment variables (see .env.example).

        A local .env file (gitignored) is loaded first when present -
        real environment variables always win over .env values.
        """
        _load_dotenv()

        def _provider(name: str) -> ProviderName | None:
            raw = os.environ.get(name, "")
            return ProviderName(raw) if raw else None

        return cls(
            provider=_provider("PROVIDER") or ProviderName.MOCK,
            segmenter_override=_provider("SEGMENTER"),
            vision_override=_provider("VISION"),
            cache_mode=CacheMode(os.environ.get("CACHE_MODE", "off")),
            cache_dir=os.environ.get("CACHE_DIR", "fixtures/recordings"),
            budget_usd=_f("BUDGET_USD", 140.0),
            budget_override=os.environ.get("BUDGET_OVERRIDE", "0") == "1",
            credits_mode=os.environ.get("CREDITS_MODE", "free"),
            meta_api_key=os.environ.get("META_API_KEY") or None,
            data_dir=os.environ.get("DATA_DIR", "data"),
            max_capture_minutes=_f("MAX_CAPTURE_MINUTES", 6.0),
            sample_fps=_f("SAMPLE_FPS", 2.0),
            sharpness_min=_f("SHARPNESS_MIN", 100.0),
            brightness_min=_f("BRIGHTNESS_MIN", 30.0),
            brightness_max=_f("BRIGHTNESS_MAX", 230.0),
            scene_change_min=_f("SCENE_CHANGE_MIN", 0.25),
            max_gap_s=_f("MAX_GAP_S", 3.0),
            max_keyframes=_i("MAX_KEYFRAMES", 80),
            propose_batch=_i("PROPOSE_BATCH", 12),
            propose_model=os.environ.get("PROPOSE_MODEL", "spark"),
            verify_frames=_i("VERIFY_FRAMES", 3),
            min_mask_score=_f("MIN_MASK_SCORE", 0.5),
            verify_mode=os.environ.get("VERIFY_MODE", "sam_plus_judge"),
            image_tokens_estimate=_i("IMAGE_TOKENS_ESTIMATE", 1200),
            routine_send_unblurred=os.environ.get("ROUTINE_SEND_UNBLURRED", "0") == "1",
            watch_fps=_f("WATCH_FPS", 1.0),
            max_calls_per_hour=_i("MAX_CALLS_PER_HOUR", 60),
            confirm_every_s=_f("CONFIRM_EVERY_S", 60.0),
            allow_contributor_for_synthetic_text=(
                os.environ.get("ALLOW_CONTRIBUTOR_FOR_SYNTHETIC_TEXT", "0") == "1"
            ),
        )
