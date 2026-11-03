"""Triage pair-ordering tests (2026-11-03): when two clips are
paired, recording time from the QuickTime metadata decides
before/after; Spark's more-problems call is only the fallback."""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _load_triage():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(
        "triage_inbox", ROOT / "scripts" / "triage_inbox.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ts(hour: int, minute: int) -> datetime:
    return datetime(2026, 11, 2, hour, minute, tzinfo=UTC)


def test_recording_time_overrides_sparks_problem_order() -> None:
    triage = _load_triage()
    created = {"a.mov": _ts(23, 21), "b.mov": _ts(23, 19)}
    before, after, basis = triage.order_pair("a.mov", "b.mov", created)
    assert (before, after) == ("b.mov", "a.mov")  # b recorded earlier
    assert basis == "recording_time"


def test_recording_time_agreeing_with_spark_keeps_order() -> None:
    triage = _load_triage()
    created = {"a.mov": _ts(23, 19), "b.mov": _ts(23, 21)}
    before, after, basis = triage.order_pair("a.mov", "b.mov", created)
    assert (before, after) == ("a.mov", "b.mov")
    assert basis == "recording_time"


def test_missing_metadata_falls_back_to_problems_visible() -> None:
    triage = _load_triage()
    created = {"a.mov": _ts(23, 19), "b.mov": None}
    before, after, basis = triage.order_pair("a.mov", "b.mov", created)
    assert (before, after) == ("a.mov", "b.mov")
    assert basis == "problems_visible"


def test_equal_recording_times_fall_back() -> None:
    triage = _load_triage()
    created = {"a.mov": _ts(23, 19), "b.mov": _ts(23, 19)}
    before, after, basis = triage.order_pair("a.mov", "b.mov", created)
    assert (before, after) == ("a.mov", "b.mov")
    assert basis == "problems_visible"
