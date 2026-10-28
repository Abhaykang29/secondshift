"""Record/replay cache tests (spec section 11.3)."""

import pytest
from secondshift.domain.enums import CacheMode
from secondshift.providers.cache import CacheMiss, RecordReplayCache, cache_key


def test_cache_key_is_deterministic() -> None:
    """Same request -> same key; different request -> different key."""
    a = cache_key("mock", "m", "ep", {"x": 1}, ["h1"])
    b = cache_key("mock", "m", "ep", {"x": 1}, ["h1"])
    c = cache_key("mock", "m", "ep", {"x": 2}, ["h1"])
    assert a == b and a != c


def test_record_then_replay_round_trip(tmp_path: object) -> None:
    """A recorded response is returned in replay mode."""
    from pathlib import Path

    root = Path(str(tmp_path))
    recorder = RecordReplayCache(root, CacheMode.RECORD)
    recorder.put("k1", {"ok": True}, model="m")
    replayer = RecordReplayCache(root, CacheMode.REPLAY)
    got = replayer.get("k1")
    assert got is not None and got["response"] == {"ok": True}


def test_replay_miss_is_an_error(tmp_path: object) -> None:
    """Replay mode must never silently call live - a miss raises."""
    from pathlib import Path

    replayer = RecordReplayCache(Path(str(tmp_path)), CacheMode.REPLAY)
    with pytest.raises(CacheMiss):
        replayer.get("missing")


def test_off_mode_stores_nothing(tmp_path: object) -> None:
    """OFF mode neither returns nor stores responses."""
    from pathlib import Path

    cache = RecordReplayCache(Path(str(tmp_path)), CacheMode.OFF)
    cache.put("k", {"ok": True}, model="m")
    assert cache.get("k") is None
