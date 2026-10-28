"""Eval tests (Phase 5): hand-computed metrics, plus the harness ablation
story - SAM verification removes the planted false positive."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from secondshift.domain.enums import ItemKind, Severity, Verification  # noqa: E402
from secondshift.domain.eval import EvalCapture, GroundTruthHazard  # noqa: E402
from secondshift.domain.hazards import Evidence, Hazard, Mask  # noqa: E402

from eval.metrics import evaluate_capture, mask_iou, prf  # noqa: E402
from eval.run_eval import run_all  # noqa: E402


def _hazard(item: str, room: str, verification: Verification) -> Hazard:
    return Hazard(
        id=f"h-{item}",
        checkup_id="c",
        pack_id="p",
        item_id=item,
        kind=ItemKind.PRESENCE,
        room=room,
        title=item,
        description="d",
        why_it_matters="w",
        severity=Severity.HIGH,
        verification=verification,
        verification_reason="r",
        evidence=Evidence(keyframe_ids=["k"], timestamps=[1.0]),
        risk_score=1.0,
    )


def test_prf_hand_computed() -> None:
    """P/R/F1 for tp=3, fp=1, fn=2 computed by hand."""
    out = prf(3, 1, 2)
    assert out == {"precision": 0.75, "recall": 0.6, "f1": round(2 * 0.75 * 0.6 / 1.35, 4)}


def test_mask_iou_hand_computed() -> None:
    """Two quarter-overlapping boxes have IoU 1/7."""
    a = Mask(keyframe_id="k", polygon=None, bbox=(0.0, 0.0, 0.5, 0.5), score=1.0, prompt="x")
    b = Mask(keyframe_id="k", polygon=None, bbox=(0.25, 0.25, 0.75, 0.75), score=1.0, prompt="x")
    assert abs(mask_iou(a, b) - 1 / 7) < 1e-9


def test_evaluate_capture_counts() -> None:
    """One TP, one FP (unmatched prediction), one FN (missed GT)."""
    capture = EvalCapture(
        capture_id="cap",
        video_path="v.mp4",
        pack_ids=["p"],
        hazards=[
            GroundTruthHazard(item_id="A", room="kitchen", time_ranges=[(0.0, 5.0)]),
            GroundTruthHazard(item_id="B", room="hallway", time_ranges=[(0.0, 5.0)]),
        ],
    )
    predicted = [
        _hazard("A", "kitchen", Verification.CONFIRMED),
        _hazard("C", "living", Verification.CONFIRMED),
        _hazard("B", "hallway", Verification.REJECTED),  # rejected = not a prediction
    ]
    result = evaluate_capture(capture, predicted, cannot_assess_count=1)
    assert (result["tp"], result["fp"], result["fn"]) == (1, 1, 1)
    assert result["confusion"]["confirmed_wrong"] == 1  # type: ignore[index]
    assert result["cannot_assess_rate"] == 0.5


def test_harness_ablation_story(tmp_path: Path) -> None:
    """spark_only keeps the false positive; spark_sam removes it."""
    payload = run_all(tmp_path / "run")
    runs = {r["config"]: r for r in payload["runs"]}  # type: ignore[index]
    assert runs["spark_only"]["totals"]["precision"] < 1.0  # type: ignore[index]
    assert runs["spark_sam"]["totals"]["precision"] == 1.0  # type: ignore[index]
    assert runs["spark_sam"]["totals"]["recall"] == 1.0  # type: ignore[index]
    assert (tmp_path / "run" / "summary.md").exists()
    assert (tmp_path / "run" / "precision_recall_by_config.png").exists()
    assert payload["compiler"]["status_accuracy"] == 1.0  # type: ignore[index]
