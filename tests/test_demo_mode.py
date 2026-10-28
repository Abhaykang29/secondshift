"""Demo-mode tests (Phase 8): the full demo script runs on mocks through
the record/replay path, and replay with an empty cache fails loudly."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from secondshift.domain.enums import CacheMode
from secondshift.providers.base import ProposeRequest
from secondshift.providers.cache import CacheMiss, RecordReplayCache
from secondshift.providers.replay import ReplayVision


def _load_demo() -> ModuleType:
    path = Path(__file__).parent.parent / "scripts" / "run_demo.py"
    spec = importlib.util.spec_from_file_location("run_demo", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_demo_runs_on_record_replay(tmp_path: Path) -> None:
    """Record once, then the whole demo script passes replay-only."""
    demo = _load_demo()
    cache_dir = tmp_path / "cache"
    demo.record_phase(cache_dir)
    summary = demo.run_demo(cache_dir)
    assert summary["parent_confirmed"] == 9
    assert summary["top_hazard"] == "FALL-FLOOR-RUG"
    assert summary["watch_alerts"] == 1
    assert summary["baby_confirmed"] == 7
    before, after = summary["recheck_score"]  # type: ignore[misc]
    assert after > before


def test_replay_with_empty_cache_is_a_loud_miss(tmp_path: Path) -> None:
    """Demo on stage can never silently fall back to a live provider."""
    cache = RecordReplayCache(tmp_path / "empty", CacheMode.REPLAY)
    vision = ReplayVision(cache, "parent_home_demo")
    with pytest.raises(CacheMiss):
        vision.propose_hazards(
            ProposeRequest(
                pack_items_yaml="",
                keyframes=[],
                narration_facts=[],
                measurements=[],
                previous_findings_summary="",
            )
        )
