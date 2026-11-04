"""Result cache + blur box cache (consistency pass, 2026-11-03).

The endpoint test runs the app with live-mode SETTINGS but mock
PROVIDERS swapped in, so the cache path (live-only) is exercised
with no network: first scan of a video computes, the identical
re-upload returns the stored report with cached=True, and ?dev=1
forces a fresh run.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from secondshift.config import Settings
from secondshift.engine_version import result_cache_key
from secondshift.main import create_app
from secondshift.providers.registry import build_providers


def test_result_cache_key_properties() -> None:
    a = result_cache_key("a" * 64, ["falls_older_adults", "fire_safety"])
    b = result_cache_key("a" * 64, ["fire_safety", "falls_older_adults"])
    assert a == b, "pack order must not change the key"
    assert a != result_cache_key("b" * 64, ["falls_older_adults", "fire_safety"])
    assert a != result_cache_key("a" * 64, ["falls_older_adults"])
    assert a != result_cache_key("a" * 64, ["falls_older_adults", "fire_safety"], verify_mode="sam")


def _tiny_video(path: Path) -> None:
    """A 4s test-pattern clip via ffmpeg. (cv2.VideoWriter output was
    intermittently undecodable at frame 1 - the flake this replaces.)"""
    import subprocess

    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=duration=4:size=320x240:rate=10",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
        capture_output=True,
    )


def _scan(client: TestClient, video: Path, dev: bool = False) -> dict:  # type: ignore[type-arg]
    created = client.post(
        "/api/checkups",
        json={
            "pack_ids": ["falls_older_adults"],
            "resident_label": "Cache test",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    )
    assert created.status_code in (200, 201), created.text[:200]
    checkup_id = created.json()["id"]
    with video.open("rb") as fh:
        uploaded = client.post(
            f"/api/checkups/{checkup_id}/captures",
            files={"file": ("clip.mp4", fh, "video/mp4")},
        )
    assert uploaded.status_code in (200, 201), uploaded.text[:200]
    capture_id = uploaded.json()["id"]
    assert uploaded.json()["video_sha256"], "upload must record the video hash"
    url = f"/api/checkups/{checkup_id}/scan" + ("?dev=1" if dev else "")
    scanned = client.post(url, json={"capture_id": capture_id})
    assert scanned.status_code == 200, scanned.text[:300]
    return scanned.json()


def test_result_cache_returns_stored_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROVIDER", "meta")  # live-mode settings...
    app = create_app()
    app.state.providers = build_providers(Settings())  # ...mock providers, no network
    client = TestClient(app)
    video = tmp_path / "clip.mp4"
    _tiny_video(video)

    first = _scan(client, video)
    assert not first.get("cached"), "first scan of a video must compute"
    second = _scan(client, video)
    assert second.get("cached") is True, "identical re-upload must hit the result cache"
    assert second["report"] == first["report"], "cached report must be the stored one, unchanged"
    fresh = _scan(client, video, dev=True)
    assert not fresh.get("cached"), "?dev=1 must bypass the cache"


def test_blur_boxes_cached_per_frame_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from secondshift.privacy import blur as blur_mod

    blur_mod._box_cache = None  # isolate from other tests/processes

    class StubSegmenter:
        def __init__(self, fail: bool = False) -> None:
            self.fail = fail

        def segment(self, ref, prompts):  # type: ignore[no-untyped-def]
            if self.fail:
                raise RuntimeError("segmenter down")

            class M:
                bbox = (0.1, 0.1, 0.5, 0.9)

            return [M()]

    frame = np.full((120, 160, 3), 90, dtype=np.uint8)
    cv2.rectangle(frame, (20, 10), (80, 110), (240, 240, 240), -1)
    one = tmp_path / "a.jpg"
    two = tmp_path / "b.jpg"  # same bytes, different path (in-process cache misses)
    cv2.imwrite(str(one), frame)
    cv2.imwrite(str(two), frame)
    assert blur_mod.blur_persons(str(one), StubSegmenter()) == 1
    assert (tmp_path / "blur_boxes.json").exists()
    # Second run of the same frame bytes: served from the hash cache,
    # so even a dead segmenter cannot change the blur.
    assert blur_mod.blur_persons(str(two), StubSegmenter(fail=True)) == 1
    blur_mod._box_cache = None


def test_concurrent_blur_of_one_frame_never_corrupts_it(tmp_path: Path) -> None:
    """Regression (2026-11-03): visualizations re-blur evidence frames
    in parallel; a direct imwrite truncated the file mid-read and
    scans intermittently died with PIL UnidentifiedImageError. Blur
    writes are atomic now - parallel blurs of one path all succeed
    and leave a valid JPEG."""
    from concurrent.futures import ThreadPoolExecutor

    from PIL import Image
    from secondshift.privacy import blur as blur_mod

    class StubSegmenter:
        def segment(self, ref, prompts):  # type: ignore[no-untyped-def]
            class M:
                bbox = (0.1, 0.1, 0.5, 0.9)

            return [M()]

    frame = np.full((120, 160, 3), 120, dtype=np.uint8)
    cv2.rectangle(frame, (20, 10), (80, 110), (240, 240, 240), -1)
    path = tmp_path / "shared.jpg"
    cv2.imwrite(str(path), frame)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: blur_mod.blur_persons(str(path), StubSegmenter()), range(8)))
    assert all(r == 1 for r in results)
    Image.open(str(path)).verify()
