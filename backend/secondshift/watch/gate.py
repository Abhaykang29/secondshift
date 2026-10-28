"""The model-call gate (spec section 9.14) - the cost control.

A candidate event may call the vision model only if: the previous call
was at least min_interval_s ago, calls this hour are under the cap, and
the daily budget (via the CostGuard price-table estimate) is not
exceeded. Everything else is decided locally or not at all.
Depends on: providers.cost.
"""

from secondshift.providers.cost import CostGuard


class ModelGate:
    """Decides whether a candidate event may spend a model call."""

    def __init__(
        self,
        cost_guard: CostGuard,
        min_interval_s: float = 10.0,
        max_calls_per_hour: int = 30,
        est_cost_per_call: float = 0.002,
    ) -> None:
        self.cost_guard = cost_guard
        self.min_interval_s = min_interval_s
        self.max_calls_per_hour = max_calls_per_hour
        self.est_cost_per_call = est_cost_per_call
        self._call_times: list[float] = []

    def allow(self, now_s: float) -> bool:
        """Whether a model call is allowed at time now_s (seconds)."""
        recent = [t for t in self._call_times if now_s - t < 3600]
        if recent and now_s - recent[-1] < self.min_interval_s:
            return False
        if len(recent) >= self.max_calls_per_hour:
            return False
        try:
            self.cost_guard.check_budget(self.est_cost_per_call)
        except Exception:
            return False
        return True

    def record_call(self, now_s: float) -> None:
        """Record a spent call (interval, hourly cap and budget ledger)."""
        self._call_times.append(now_s)
        self.cost_guard.record(
            "watch", "muse-spark-1.3", "chat", self.est_cost_per_call, self.est_cost_per_call
        )
