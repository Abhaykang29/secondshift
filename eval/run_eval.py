"""Eval runner entry point (Phase 5 implements the full harness).

Usage: python eval/run_eval.py --dataset <id> --config <name>
Writes eval/reports/<timestamp>/summary.md, summary.json and charts.
"""

import argparse


def main() -> None:
    """Parse args; the harness itself lands in Phase 5."""
    parser = argparse.ArgumentParser(description="SecondShift eval harness")
    parser.add_argument("--dataset", default="mock")
    parser.add_argument("--config", default="spark_sam")
    args = parser.parse_args()
    print(f"eval: dataset={args.dataset} config={args.config} - harness lands in Phase 5.")


if __name__ == "__main__":
    main()
