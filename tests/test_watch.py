"""Watch tests (Phase 6): room guard, health, gate, state machine, engine."""

import numpy as np
import pytest
from secondshift.domain.watch import WatchSource
from secondshift.privacy.room_guard import WatchRefused, assert_watch_allowed
from secondshift.providers.cost import CostGuard
from secondshift.watch import health
from secondshift.watch.engine import WatchEngine
from secondshift.watch.gate import ModelGate
from secondshift.watch.state_machine import StateMachine


def test_bathroom_watch_is_always_refused() -> None:
    """Even with consent, a bathroom source raises the product refusal."""
    source = WatchSource(id="s", kind="phone", label="x", resident_consent=True)
    with pytest.raises(WatchRefused, match="can't watch in a bathroom"):
        assert_watch_allowed(source, "bathroom")


def test_bedroom_needs_resident_consent() -> None:
    """Bedroom without resident consent refuses; with consent it passes."""
    source = WatchSource(id="s", kind="phone", label="x", resident_consent=False)
    with pytest.raises(WatchRefused):
        assert_watch_allowed(source, "bedroom")
    ok = WatchSource(id="s", kind="phone", label="x", resident_consent=True)
    assert_watch_allowed(ok, "bedroom")


def test_health_detectors_on_synthetic_frames() -> None:
    """Dark, uniform and frozen detection on numpy frames."""
    dark = np.zeros((50, 50, 3), dtype=np.uint8)
    assert health.is_dark(dark) and health.is_uniform(dark)
    rng = np.random.default_rng(0)
    noisy = rng.integers(0, 255, (50, 50, 3), dtype=np.uint8)
    assert not health.is_dark(noisy) and not health.is_uniform(noisy)
    hashes = [health.frame_hash(dark)] * 31
    assert health.is_frozen(hashes)
    moved_ref = health.descriptor(noisy)
    assert health.camera_moved(moved_ref, health.descriptor(dark))


def test_gate_enforces_interval_and_hourly_cap() -> None:
    """Calls inside the min interval or past the hourly cap are refused."""
    gate = ModelGate(CostGuard(), min_interval_s=10.0, max_calls_per_hour=2)
    assert gate.allow(0.0)
    gate.record_call(0.0)
    assert not gate.allow(5.0)  # too soon
    assert gate.allow(11.0)
    gate.record_call(11.0)
    assert not gate.allow(100.0)  # hourly cap of 2 reached


def _engine() -> WatchEngine:
    return WatchEngine(StateMachine("src", "rule"), ModelGate(CostGuard(), min_interval_s=0.0))


def test_gate_open_40s_produces_exactly_one_alert() -> None:
    """Spec demo moment: gate open >30s on the synthetic timeline = 1 alert."""
    timeline = [(float(t), 10 <= t < 50) for t in range(0, 121, 5)]
    events = _engine().run_duration_rule(timeline, 30.0, "baby gate")
    alerts = [e for e in events if e.state_to.value == "alert"]
    assert len(alerts) == 1
    assert alerts[0].outcome.value == "met"


def test_flapping_gate_never_alerts() -> None:
    """Open/closed flapping every 10s never sustains 30s - no alert."""
    timeline = [(float(t), (t // 10) % 2 == 0) for t in range(0, 121, 5)]
    events = _engine().run_duration_rule(timeline, 30.0, "baby gate")
    assert not [e for e in events if e.state_to.value == "alert"]


def test_sustained_open_then_close_then_open_alerts_once_per_episode() -> None:
    """Two separate episodes = two alerts; one episode never double-alerts."""
    timeline = (
        [(float(t), True) for t in range(0, 45, 5)]
        + [(float(t), False) for t in range(45, 60, 5)]
        + [(float(t), True) for t in range(60, 105, 5)]
    )
    events = _engine().run_duration_rule(timeline, 30.0, "baby gate")
    assert len([e for e in events if e.state_to.value == "alert"]) == 2


def test_dark_frames_move_rule_to_cannot_see() -> None:
    """A run of black frames yields one cannot_see transition, then recovery."""
    dark = np.zeros((40, 40, 3), dtype=np.uint8)
    bright = np.random.default_rng(1).integers(100, 255, (40, 40, 3), dtype=np.uint8)
    frames = [(0.0, dark), (1.0, dark), (2.0, bright)]
    events = _engine().health_events_for_frames(frames, "stove")
    states = [e.state_to.value for e in events]
    assert states == ["watching", "cannot_see", "watching"]


def test_deadline_rule_alerts_when_event_never_happens() -> None:
    """Pill box never opened by the deadline = one alert at the deadline."""
    timeline = [(float(t), False) for t in range(0, 70, 10)]
    events = _engine().run_deadline_rule(timeline, 60.0, "pill box opening")
    assert len([e for e in events if e.state_to.value == "alert"]) == 1
    timeline2 = [(float(t), t >= 30) for t in range(0, 70, 10)]
    events2 = _engine().run_deadline_rule(timeline2, 60.0, "pill box opening")
    assert not [e for e in events2 if e.state_to.value == "alert"]
