"""Watch engine (spec section 9.14): candidate logic on top of the gate.

The engine evaluates local candidates frame by frame; when a duration
threshold is crossed it asks the judge ONCE (through the gate) before
alerting. Condition evaluation is injected (a callable returning
True/False/None per timestamp) so the same engine runs on SAM masks in
production and on scripted sequences in tests - the alert behaviour
(exactly one alert per episode) is what's under test.
Depends on: watch.state_machine, watch.gate, watch.health, domain.watch.
"""

from collections.abc import Callable, Iterable

import numpy as np

from secondshift.domain.watch import WatchEvent
from secondshift.watch import health
from secondshift.watch.gate import ModelGate
from secondshift.watch.state_machine import StateMachine

ConditionFn = Callable[[float], bool | None]


class WatchEngine:
    """Runs compiled duration/deadline rules over frame timestamps."""

    def __init__(
        self,
        machine: StateMachine,
        gate: ModelGate,
        judge_confirm: Callable[[], bool] | None = None,
    ) -> None:
        self.machine = machine
        self.gate = gate
        self.judge_confirm = judge_confirm or (lambda: True)

    def run_duration_rule(
        self,
        timeline: Iterable[tuple[float, bool | None]],
        duration_s: float,
        label: str,
    ) -> list[WatchEvent]:
        """STATE_FOR_DURATION / OBJECT_STATE-with-duration evaluation.

        timeline yields (t_seconds, condition_present). The alert fires
        when the condition has been continuously present for duration_s,
        confirmed through the gate + judge; flapping resets the clock.
        """
        events: list[WatchEvent] = []
        start = self.machine.start()
        events.append(start)
        present_since: float | None = None
        for t, present in timeline:
            if present is None:
                event = self.machine.health_failed(f"I can't see the {label}.")
                if event:
                    events.append(event)
                present_since = None
                continue
            if self.machine.state.value == "cannot_see":
                recovered = self.machine.health_recovered()
                if recovered:
                    events.append(recovered)
            if present:
                if present_since is None:
                    present_since = t
                    seen = self.machine.condition_seen(f"The {label} condition appeared.")
                    if seen:
                        events.append(seen)
                elif t - present_since >= duration_s:
                    if self.gate.allow(t):
                        self.gate.record_call(t)
                        if self.judge_confirm():
                            met = self.machine.condition_met(
                                f"Confirmed: the {label} condition lasted {duration_s:.0f} seconds."
                            )
                            if met:
                                events.append(met)
            else:
                if present_since is not None:
                    cleared = self.machine.condition_cleared()
                    if cleared:
                        events.append(cleared)
                present_since = None
        return events

    def run_deadline_rule(
        self,
        timeline: Iterable[tuple[float, bool]],
        deadline_s: float,
        label: str,
    ) -> list[WatchEvent]:
        """EVENT_BY_DEADLINE: alert at the deadline if the event never happened."""
        events: list[WatchEvent] = [self.machine.start()]
        happened = False
        for t, occurred in timeline:
            if occurred and not happened:
                happened = True
                seen = self.machine.condition_seen(f"The {label} happened in time.")
                if seen:
                    events.append(seen)
                cleared = self.machine.condition_cleared("Done for today.")
                if cleared:
                    events.append(cleared)
            if t >= deadline_s and not happened:
                pending = (
                    self.machine.condition_seen(f"The {label} has not happened yet.")
                    if self.machine.state.value == "watching"
                    else None
                )
                if pending:
                    events.append(pending)
                if self.gate.allow(t):
                    self.gate.record_call(t)
                    if self.judge_confirm():
                        met = self.machine.condition_met(
                            f"Deadline passed and the {label} never happened."
                        )
                        if met:
                            events.append(met)
                break
        return events

    def health_events_for_frames(
        self,
        frames: Iterable[tuple[float, np.ndarray]],
        label: str,
    ) -> list[WatchEvent]:
        """Camera-health pass over real frames: dark/uniform/frozen -> cannot_see."""
        events: list[WatchEvent] = [self.machine.start()]
        hashes: list[str] = []
        for _t, frame in frames:
            hashes.append(health.frame_hash(frame))
            bad = health.is_dark(frame) or health.is_uniform(frame) or health.is_frozen(hashes)
            if bad:
                event = self.machine.health_failed(f"I can't see the {label}.")
                if event:
                    events.append(event)
            elif self.machine.state.value == "cannot_see":
                recovered = self.machine.health_recovered()
                if recovered:
                    events.append(recovered)
        return events
