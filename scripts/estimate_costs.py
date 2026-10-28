"""Estimate the cost of one check-up scan from config prices.

Uses the cost guard estimators so the numbers match what the app enforces.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondshift.config import MODEL_IDS  # noqa: E402
from secondshift.providers.cost import CostGuard  # noqa: E402


def main() -> None:
    """Print a rough per-scan estimate at default settings."""
    guard = CostGuard()
    propose = guard.estimate_chat(MODEL_IDS["fast"], n_images=60)
    verify = guard.estimate_segment(MODEL_IDS["segment"], n_images=30)
    print(f"Propose (Spark, 60 keyframes): ~${propose:.3f}")
    print(f"Verify (SAM, 30 images): ~${verify:.3f}")
    print(f"Total rough estimate: ~${propose + verify:.3f} per scan (estimates only)")


if __name__ == "__main__":
    main()
