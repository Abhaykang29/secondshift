"""Capture tests (Phase 1): synthetic video -> probe -> frames -> keyframes."""

import subprocess
import sys
from pathlib import Path

import pytest
from secondshift.capture.keyframes import select_keyframes
from secondshift.capture.narration import extract_facts
from secondshift.capture.probe import CaptureTooLong, probe_video
from secondshift.capture.quality import frame_metrics
from secondshift.domain.checkup import NarrationSegment

ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def synthetic_video(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Generate the synthetic video once per module (it takes a second)."""
    out = tmp_path_factory.mktemp("synth") / "synthetic.mp4"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "make_synthetic_video.py"), "--out", str(out)],
        check=True,
        capture_output=True,
    )
    return str(out)


def test_synthetic_video_probes_as_60_seconds(synthetic_video: str) -> None:
    """The synthetic video is 60s, 640x360, with no audio track."""
    probe = probe_video(synthetic_video)
    assert probe.duration_s == pytest.approx(60.0, abs=1.0)
    assert (probe.width, probe.height) == (640, 360)
    assert probe.has_audio is False


def test_probe_rejects_over_long_video(synthetic_video: str) -> None:
    """A video past the configured cap raises the friendly error."""
    with pytest.raises(CaptureTooLong):
        probe_video(synthetic_video, max_minutes=0.5)


def test_synthetic_video_produces_40_to_80_keyframes(synthetic_video: str) -> None:
    """Phase 1 acceptance: the synthetic video yields 40-80 usable keyframes."""
    from secondshift.capture.extract import extract_frames

    frames_dir = Path(synthetic_video).parent / "frames"
    frames = extract_frames(synthetic_video, str(frames_dir), 2.0)
    assert len(frames) == 120
    keyframes = select_keyframes(frames, "cap-test", 2.0, change_min=0.25 / 16)
    assert 40 <= len(keyframes) <= 80
    assert all(k.usable for k in keyframes)
    times = [k.t for k in keyframes]
    assert times == sorted(times)


def test_sharpness_of_blank_frame_is_near_zero() -> None:
    """A flat frame has ~0 Laplacian variance and mid brightness."""
    import numpy as np

    sharpness, brightness = frame_metrics(np.full((100, 100, 3), 128, dtype=np.uint8))
    assert sharpness == pytest.approx(0.0, abs=0.01)
    assert brightness == pytest.approx(128.0, abs=1.0)


def test_narration_facts_keep_space_facts_and_drop_health() -> None:
    """Facts: 'twice a night to the bathroom' survives; diagnoses are dropped."""
    segments = [
        NarrationSegment(
            capture_id="c",
            t_start=30.0,
            t_end=34.0,
            text="Mom gets up twice a night to use the bathroom.",
            language="en",
        ),
        NarrationSegment(
            capture_id="c",
            t_start=40.0,
            t_end=43.0,
            text="She was diagnosed with diabetes last year near the kitchen.",
            language="en",
        ),
    ]
    facts = extract_facts(segments)
    assert len(facts) == 1
    assert "night_path" in facts[0].affects
