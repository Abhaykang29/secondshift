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



def test_select_keyframes_falls_back_when_every_frame_is_soft(tmp_path: Path) -> None:
    """Regression (2026-11-03): a real 120fps phone clip scored
    sharpness 24-75 on every sampled frame against the 100 floor, so
    selection stored ZERO keyframes and the scan crashed on the
    empty list. When frames are decodable but all fail the quality
    gates, the selector must admit the sharpest ones instead of
    returning nothing."""
    import cv2
    import numpy as np

    rng = np.random.default_rng(7)
    paths: list[Path] = []
    for i in range(6):
        image = rng.integers(0, 255, (240, 320, 3), dtype=np.uint8)
        soft = cv2.GaussianBlur(image, (0, 0), sigmaX=6)  # very soft
        path = tmp_path / f"frame_{i:05d}.jpg"
        cv2.imwrite(str(path), soft)
        paths.append(path)
    kept = select_keyframes(paths, "cap-soft", 2.0)
    assert kept, "fallback must never return zero keyframes for decodable frames"
    assert all(k.image_path in {str(p) for p in paths} for k in kept)
    assert [k.t for k in kept] == sorted(k.t for k in kept)


def test_scan_rejects_a_capture_with_an_empty_keyframe_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stored capture whose keyframe list is empty must 422 with a
    plain message instead of crashing inside the scan pipeline."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROVIDER", "mock")
    from fastapi.testclient import TestClient
    from secondshift.main import create_app

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    created = client.post(
        "/api/checkups",
        json={
            "pack_ids": ["falls_older_adults"],
            "resident_label": "Empty capture test",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    )
    assert created.status_code in (200, 201)
    checkup_id = created.json()["id"]
    app.state.store.put("keyframes", "cap-empty", {"keyframes": []})
    resp = client.post(
        f"/api/checkups/{checkup_id}/scan", json={"capture_id": "cap-empty"}
    )
    assert resp.status_code == 422
    assert "no usable frames" in resp.json()["detail"]


def test_select_keyframes_guarantees_timeline_coverage(tmp_path: Path) -> None:
    """Regression (2026-11-03): 92d's real sharpness profile - most
    frames score 12-34 (below the 100 floor), a few late frames pass.
    The old selector returned only t=31-32.5s keyframes, so the
    clip's first 25 seconds never reached the model. Every ~2s
    window must now contribute its sharpest frame, marked
    low_sharpness when below the floor."""
    import cv2
    import numpy as np

    rng = np.random.default_rng(11)
    paths: list[Path] = []
    for i in range(76):  # 38s at 2fps, like the real clip
        image = rng.integers(0, 255, (240, 320, 3), dtype=np.uint8)
        if 62 <= i <= 66:
            frame = image  # the sharp late segment (t=31-33s)
        else:
            frame = cv2.GaussianBlur(image, (0, 0), sigmaX=12)  # very soft
        path = tmp_path / f"frame_{i:05d}.jpg"
        cv2.imwrite(str(path), frame)
        paths.append(path)
    kept = select_keyframes(paths, "cap-coverage", 2.0)
    assert kept, "coverage must return keyframes"
    assert kept[0].t <= 2.0, f"clip start uncovered: first t={kept[0].t}"
    assert kept[-1].t >= 36.0, f"clip end uncovered: last t={kept[-1].t}"
    windows = {int(k.t // 2.0) for k in kept}
    assert windows == set(range(19)), f"uncovered windows: {set(range(19)) - windows}"
    early = [k for k in kept if k.t < 30.0]
    assert early and all(k.low_sharpness for k in early), (
        "below-floor coverage frames must be marked low_sharpness"
    )
    assert len(kept) <= 80
