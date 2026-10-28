"""Eval harness (spec section 10.4).

Runs the scan pipeline over every manifest capture for each ablation
config and writes eval/reports/<timestamp>/ with results.json,
summary.md and charts. On mocks the numbers measure the harness and the
scenario design - they are NOT product accuracy (labels are the
scenario's own; real accuracy needs TODO(TEAM) human-labelled captures).

Usage: python eval/run_eval.py [--config spark_sam] [--out DIR]
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml  # noqa: E402
from secondshift.checklists.loader import load_all_packs  # noqa: E402
from secondshift.config import Settings  # noqa: E402
from secondshift.domain.checkup import Checkup, Consent, Keyframe  # noqa: E402
from secondshift.domain.eval import EvalCapture, GroundTruthHazard  # noqa: E402
from secondshift.pipeline.scan import ScanInput, run_scan  # noqa: E402
from secondshift.providers.cost import CostGuard  # noqa: E402
from secondshift.providers.registry import build_providers  # noqa: E402
from secondshift.rules.compiler import compile_rule  # noqa: E402

from eval.metrics import aggregate, evaluate_capture  # noqa: E402

ROOT = Path(__file__).parent.parent
CONFIGS = {
    "spark_only": {"propose_model": "spark", "verify_mode": "none"},
    "spark_sam": {"propose_model": "spark", "verify_mode": "sam"},
    "wonder_only": {"propose_model": "wonder", "verify_mode": "none"},
    "wonder_sam": {"propose_model": "wonder", "verify_mode": "sam_plus_judge"},
}
_MODEL_FOR_COST = {"spark": "muse-spark-1.3", "wonder": "muse-wonder-1.0"}


def _load_manifest() -> list[EvalCapture]:
    data = yaml.safe_load((ROOT / "eval" / "synthetic_manifest.yaml").read_text())
    captures = []
    for entry in data["captures"]:
        captures.append(
            EvalCapture(
                capture_id=entry["capture_id"],
                video_path=entry["video_path"],
                pack_ids=entry["pack_ids"],
                hazards=[GroundTruthHazard(**gt) for gt in entry["hazards"]],
            )
        )
    return captures


def _keyframes() -> list[Keyframe]:
    return [
        Keyframe(
            id=f"eval-kf-{i:03d}",
            capture_id="eval",
            t=float(i * 5),
            image_path="",
            sharpness=500.0,
            brightness=120.0,
            usable=True,
        )
        for i in range(20)
    ]


def run_config(config_name: str, captures: list[EvalCapture]) -> dict[str, object]:
    """Run one ablation config over all captures."""
    config = CONFIGS[config_name]
    packs_by_id = load_all_packs()
    guard = CostGuard()
    results = []
    started = time.perf_counter()
    for capture in captures:
        providers = build_providers(Settings())
        checkup = Checkup(
            id=f"eval-{capture.capture_id}",
            created_at=datetime.now(UTC),
            pack_ids=capture.pack_ids,
            consent=Consent(resident_informed=True, no_private_moments=True),
        )
        output = run_scan(
            providers,
            ScanInput(
                checkup=checkup,
                packs=[packs_by_id[capture.pack_ids[0]]],
                keyframes=_keyframes(),
                scenario_name=capture.capture_id,
                verify_mode=str(config["verify_mode"]),
            ),
        )
        results.append(evaluate_capture(capture, output.hazards, len(output.cannot_assess)))
        # Estimated cost from the section 11.4 price table (not measured billing).
        model = _MODEL_FOR_COST[str(config["propose_model"])]
        est = guard.estimate_chat(model, n_images=20)
        if config["verify_mode"] != "none":
            est += guard.estimate_segment("sam-3.1", n_images=10)
    latency = time.perf_counter() - started
    totals = aggregate(results)
    return {
        "config": config_name,
        **config,
        "captures": results,
        "totals": totals,
        "estimated_cost_usd": round(est * len(captures), 4),
        "wall_time_s": round(latency, 2),
        "note": "Mock providers: latency/cost are harness measurements + price-table estimates.",
    }


def compiler_metrics() -> dict[str, object]:
    """Rule-compiler accuracy on the Appendix B sentences."""
    sentences = yaml.safe_load((ROOT / "eval" / "rules" / "sentences.yaml").read_text())
    status_ok = prim_ok = total_compiled = 0
    for entry in sentences:
        spec = compile_rule(entry["text"], entry["mode_hint"])
        if spec.status.value == entry["expected_status"]:
            status_ok += 1
        if entry["expected_status"] == "compiled":
            total_compiled += 1
            if sorted(c.primitive.value for c in spec.conditions) == sorted(
                entry["expected_primitives"]
            ):
                prim_ok += 1
    n = len(sentences)
    return {
        "sentences": n,
        "status_accuracy": round(status_ok / n, 4),
        "primitive_accuracy_on_compiled": round(prim_ok / max(1, total_compiled), 4),
    }


def run_all(out_dir: Path, only: str | None = None) -> dict[str, object]:
    """Run all (or one) configs and write the report bundle."""
    captures = _load_manifest()
    names = [only] if only else list(CONFIGS)
    runs = [run_config(name, captures) for name in names]
    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": "synthetic scenarios (mock labels - NOT human-labelled ground truth)",
        "runs": runs,
        "compiler": compiler_metrics(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2))
    lines = [
        "# SecondShift eval summary",
        "",
        f"Dataset: {payload['dataset']}",
        "",
        "| Config | Precision | Recall | F1 | Est. cost | Wall time |",
        "|---|---|---|---|---|---|",
    ]
    for run in runs:
        totals = run["totals"]  # type: ignore[index]
        lines.append(
            f"| {run['config']} | {totals['precision']} | {totals['recall']} | "
            f"{totals['f1']} | ${run['estimated_cost_usd']} | {run['wall_time_s']}s |"
        )
    comp = payload["compiler"]  # type: ignore[index]
    lines += [
        "",
        f"Rule compiler: status accuracy {comp['status_accuracy']}, "
        f"primitive accuracy {comp['primitive_accuracy_on_compiled']} "
        f"on {comp['sentences']} Appendix B sentences.",
        "",
        "Honest note: mock numbers validate the harness, not the product.",
        "Real accuracy requires TODO(TEAM) human-labelled captures.",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")
    _charts(runs, out_dir)
    return payload


def _charts(runs: list[dict[str, object]], out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = [str(r["config"]) for r in runs]
    precisions = [float(r["totals"]["precision"]) for r in runs]  # type: ignore[index]
    recalls = [float(r["totals"]["recall"]) for r in runs]  # type: ignore[index]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(names))
    ax.bar([i - 0.2 for i in x], precisions, width=0.4, label="precision")
    ax.bar([i + 0.2 for i in x], recalls, width=0.4, label="recall")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.set_title("Precision / recall by ablation config (mock scenarios)")
    fig.tight_layout()
    fig.savefig(out_dir / "precision_recall_by_config.png", dpi=120)
    plt.close(fig)
    costs = [float(r["estimated_cost_usd"]) for r in runs]
    times = [float(r["wall_time_s"]) for r in runs]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(names, costs, label="estimated cost USD")
    ax.bar(names, times, bottom=costs, label="wall time s (stacked, different unit - read axes)")
    ax.legend()
    ax.set_title("Estimated cost and wall time by config")
    fig.tight_layout()
    fig.savefig(out_dir / "cost_latency.png", dpi=120)
    plt.close(fig)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the SecondShift eval harness")
    parser.add_argument("--config", default=None, choices=list(CONFIGS))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out) if args.out else ROOT / "eval" / "reports" / stamp
    payload = run_all(out, args.config)
    print(f"Wrote {out}")
    print(json.dumps(payload["compiler"], indent=2))


if __name__ == "__main__":
    main()
