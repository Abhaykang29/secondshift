"""Eval metrics (spec section 15.2).

Why: matching and metrics must be unit-tested against hand-computed
examples before any number is shown in a demo. Phase 5 implements the
greedy one-to-one matching; Phase 0 fixes the summary shape.
Depends on: domain.eval.
"""


def f1_score(precision: float, recall: float) -> float:
    """Harmonic mean of precision and recall (0 when both are 0)."""
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
