"""Cost guard tests (spec section 11.4)."""

import pytest
from secondshift.providers.cost import BudgetExceeded, CostGuard


def test_estimate_chat_uses_price_table_and_image_estimate() -> None:
    """Spark: 1 image = 1500 image tokens + 500 text, 800 output tokens."""
    guard = CostGuard()
    est = guard.estimate_chat("muse-spark-1.3", n_images=1)
    expected = 2000 / 1_000_000 * 1.25 + 800 / 1_000_000 * 4.25
    assert est == pytest.approx(expected)


def test_budget_hard_stop_raises() -> None:
    """Spending that would cross the budget raises BudgetExceeded."""
    guard = CostGuard(budget_usd=1.00)
    guard.record("vision", "muse-spark-1.3", "chat", 0.90, 0.90)
    with pytest.raises(BudgetExceeded):
        guard.check_budget(0.20)


def test_budget_override_disables_hard_stop() -> None:
    """The env-var override is the only way past the hard stop."""
    guard = CostGuard(budget_usd=0.01, override=True)
    guard.check_budget(100.0)  # must not raise


def test_ledger_accumulates_actual_spend() -> None:
    """spent_usd is the sum of actual costs, not estimates."""
    guard = CostGuard()
    guard.record("segment", "sam-3.1", "segment", est_cost_usd=0.10, actual_cost_usd=0.08)
    guard.record("segment", "sam-3.1", "segment", est_cost_usd=0.10, actual_cost_usd=0.08)
    assert guard.spent_usd == pytest.approx(0.16)
