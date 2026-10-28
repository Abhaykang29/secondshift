"""Watch rule state machine (spec section 9.14).

States: idle -> watching -> pending (condition seen, waiting for its
duration/deadline) -> alert (outcome sent) -> watching ...; cannot_see
from any state on a camera-health failure*. (*Only CAMERA_HEALTH
conditions may alert out of cannot_see.) One alert per episode: after an
alert, the condition must clear before it can alert again.
Depends on: domain.enums, domain.watch.
"""

import uuid
from datetime import UTC, datetime

from secondshift.domain.enums import Outcome, RuleState
from secondshift.domain.watch import WatchEvent


class StateMachine:
    """Tracks one rule on one source and emits transition events."""

    def __init__(self, source_id: str, rule_id: str) -> None:
        self.source_id = source_id
        self.rule_id = rule_id
        self.state: RuleState = RuleState.IDLE
        self._alerted_this_episode = False

    def _emit(self, to: RuleState, outcome: Outcome, reason: str) -> WatchEvent:
        event = WatchEvent(
            id=uuid.uuid4().hex,
            source_id=self.source_id,
            rule_id=self.rule_id,
            at=datetime.now(UTC),
            state_from=self.state,
            state_to=to,
            outcome=outcome,
            reason=reason,
        )
        self.state = to
        return event

    def start(self) -> WatchEvent:
        """idle -> watching when the watch begins."""
        return self._emit(RuleState.WATCHING, Outcome.CANNOT_TELL, "Watch started.")

    def condition_seen(self, reason: str) -> WatchEvent | None:
        """watching -> pending when the condition first appears."""
        if self.state is RuleState.WATCHING:
            return self._emit(RuleState.PENDING, Outcome.CANNOT_TELL, reason)
        return None

    def condition_met(self, reason: str) -> WatchEvent | None:
        """pending -> alert when duration/deadline confirms. One per episode."""
        if self.state is RuleState.PENDING and not self._alerted_this_episode:
            self._alerted_this_episode = True
            return self._emit(RuleState.ALERT, Outcome.MET, reason)
        return None

    def condition_cleared(self, reason: str = "The condition cleared.") -> WatchEvent | None:
        """pending/alert -> watching when the condition goes away."""
        if self.state in (RuleState.PENDING, RuleState.ALERT):
            self._alerted_this_episode = False
            return self._emit(RuleState.WATCHING, Outcome.NOT_MET, reason)
        return None

    def health_failed(self, reason: str) -> WatchEvent | None:
        """any -> cannot_see on a camera-health failure (once per episode)."""
        if self.state is not RuleState.CANNOT_SEE:
            return self._emit(RuleState.CANNOT_SEE, Outcome.CANNOT_TELL, reason)
        return None

    def health_recovered(self, reason: str = "The camera can see again.") -> WatchEvent | None:
        """cannot_see -> watching when health recovers."""
        if self.state is RuleState.CANNOT_SEE:
            return self._emit(RuleState.WATCHING, Outcome.CANNOT_TELL, reason)
        return None
