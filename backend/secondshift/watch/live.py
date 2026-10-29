"""Live Watch loop (pass 2 Phase G) - REAL frames, real models.

One LiveWatch consumes frames from a FrameSource (the phone hub today;
a file replay in tests), and for each frame:

1. health (dark / uniform / frozen) -> CANNOT_SEE via the state machine
2. change detection vs the running background (cheap, no model)
3. model gate (min interval + hourly cap + budget) before any model call
4. SAM finds the condition targets; Spark judges states that boxes
   can't decide (open vs closed) via prompts/watch_state.md, cached
   per frame hash so repeats are free
5. the shared StateMachine turns condition + duration into events

Events are appended to the JSON store (collection "watch_events") and
pushed to SSE subscribers. Room classification (G.3) happens at setup:
Spark classifies a snapshot via prompts/room_type.md; the user
confirms or corrects; bathroom if EITHER says bathroom -> refused;
bedroom needs explicit resident consent.

NOT VERIFIED LIVE yet: unit tests drive this class with synthetic
frames and stub providers. Live acceptance (real phone, real gate)
runs when the team films watch_gate.mp4 (docs/LIVE_VERIFICATION.md).
Depends on: watch.state_machine/health/change/gate, providers.base.
"""

import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from secondshift.domain.enums import Primitive, RuleState
from secondshift.domain.rules import RuleSpec
from secondshift.domain.watch import WatchEvent
from secondshift.providers.base import ImageRef
from secondshift.providers.registry import Providers
from secondshift.watch.change import ChangeDetector
from secondshift.watch.gate import ModelGate
from secondshift.watch.health import frame_hash, is_dark, is_frozen, is_uniform
from secondshift.watch.state_machine import StateMachine

GATE_EVERY_S = 5.0
CHANGE_TRIGGER = 0.02


def classify_watch_room(
    snapshot_path: str,
    claimed_room: str,
    providers: Providers,
) -> tuple[str, bool, str]:
    """Classify the room and apply the guard. Returns (room, allowed, reason).

    The classifier's answer and the user's claim are combined
    conservatively: bathroom on EITHER side refuses the watch.
    """
    verdict = providers.vision.classify_room(ImageRef(path=snapshot_path))
    model_room = str(verdict.get("room_type", "")).strip().lower() if verdict else ""
    room = model_room or claimed_room.strip().lower()
    if room == "bathroom" or claimed_room.strip().lower() == "bathroom":
        return "bathroom", False, "Watches are never allowed in bathrooms."
    return room, True, f"Room: {room} (model: {model_room or 'no answer'}; you said: {claimed_room})."


class LiveWatch:
    """One live watch: a compiled rule on one frame source."""

    def __init__(
        self,
        spec: RuleSpec,
        source_id: str,
        providers: Providers,
        work_dir: str,
        on_event: Callable[[WatchEvent], None] | None = None,
    ) -> None:
        self.spec = spec
        self.source_id = source_id
        self.providers = providers
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.machine = StateMachine(source_id, spec.id)
        self.detector = ChangeDetector()
        self.gate = ModelGate(providers.cost, min_interval_s=GATE_EVERY_S)
        self.on_event = on_event
        self._hashes: list[str] = []
        self._last_gate_s = 0.0
        self._condition_since: float | None = None
        self._state_cache: dict[str, bool] = {}
        self._started = False

    # -- internals ---------------------------------------------------
    def _emit(self, event: WatchEvent | None) -> list[WatchEvent]:
        if event is None:
            return []
        if self.on_event:
            self.on_event(event)
        return [event]

    def _duration_s(self) -> float:
        for cond in self.spec.conditions:
            if cond.duration_min:
                return float(cond.duration_min) * 60.0
        return 0.0

    def _targets(self) -> list[str]:
        return [c.target for c in self.spec.conditions if c.target]

    def _condition_holds(self, frame: np.ndarray, now_s: float) -> bool | None:
        """Ask SAM + the state judge whether the rule condition holds.

        Returns None when the frame can't be judged (no targets found
        and the condition is about presence - treated as not holding;
        state rules with no visible target return None = cannot tell).
        """
        path = self.work_dir / "live-frame.jpg"
        cv2.imwrite(str(path), frame)
        digest = frame_hash(frame)
        if digest in self._state_cache:
            return self._state_cache[digest]
        ref = ImageRef(path=str(path), keyframe_id=f"live-{digest[:8]}")
        holds = False
        saw_any = False
        for cond in self.spec.conditions:
            if not cond.target:
                continue
            masks = self.providers.segmenter.segment(ref, [cond.target])
            present = len(masks) > 0
            if cond.primitive is Primitive.OBJECT_PRESENT:
                saw_any = saw_any or present
                holds = holds or present
            elif cond.primitive is Primitive.ZONE_EMPTY_FOR_DURATION:
                people = self.providers.segmenter.segment(ref, ["person"])
                saw_any = True
                holds = holds or len(people) == 0
            elif cond.primitive in (Primitive.OBJECT_STATE, Primitive.STATE_FOR_DURATION):
                if not present:
                    continue
                saw_any = True
                state = self.providers.vision.judge_state(
                    cond.target,
                    f"Is the {cond.target} {cond.target_state or 'in the watched state'}?",
                    ref,
                )
                if state is None or state == "cannot_tell":
                    return None
                holds = holds or (state == (cond.target_state or state))
        result = holds if saw_any else False
        self._state_cache[digest] = result
        return result

    # -- the loop step -------------------------------------------------
    def process_frame(self, frame: np.ndarray, now_s: float | None = None) -> list[WatchEvent]:
        """Process one frame; returns any events it produced."""
        now = time.monotonic() if now_s is None else now_s
        events: list[WatchEvent] = []
        if not self._started:
            self._started = True
            events += self._emit(self.machine.start())
        self._hashes.append(frame_hash(frame))
        if is_dark(frame) or is_uniform(frame) or is_frozen(self._hashes):
            events += self._emit(
                self.machine.health_failed("The camera can't see (dark, covered or frozen).")
            )
            return events
        if self.machine.state is RuleState.CANNOT_SEE:
            events += self._emit(self.machine.health_recovered())
        changed = self.detector.change_fraction(frame)
        due = now - self._last_gate_s >= GATE_EVERY_S
        if not (due or changed >= CHANGE_TRIGGER):
            return events
        if not self.gate.allow(now):
            return events
        self.gate.record_call(now)
        self._last_gate_s = now
        holds = self._condition_holds(frame, now)
        if holds is None:
            return events
        duration = self._duration_s()
        if holds:
            if self._condition_since is None:
                self._condition_since = now
                events += self._emit(
                    self.machine.condition_seen(f"{self.spec.human_summary} - checking duration.")
                )
            if duration == 0 or now - self._condition_since >= duration:
                events += self._emit(
                    self.machine.condition_met(self.spec.human_summary)
                )
        else:
            self._condition_since = None
            events += self._emit(self.machine.condition_cleared())
        return events
