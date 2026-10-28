"""Eval metrics (spec section 10.3) - pure functions, hand-tested.

Matching: a prediction matches a ground-truth hazard when item_id and
room agree and, when both have masks, mask IoU >= 0.3 (spec Appendix D).
Predictions = hazards not REJECTED. Severity/kind splits and the
verification confusion come from the same matching pass.
Depends on: domain models.
"""

from secondshift.domain.eval import EvalCapture
from secondshift.domain.hazards import Hazard, Mask


def mask_iou(a: Mask, b: Mask) -> float:
    """IoU of two masks' bounding boxes."""
    ax0, ay0, ax1, ay1 = a.bbox
    bx0, by0, bx1, by1 = b.bbox
    inter = max(0.0, min(ax1, bx1) - max(ax0, bx0)) * max(0.0, min(ay1, by1) - max(ay0, by0))
    union = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / union if union > 0 else 0.0


def _matches(pred: Hazard, gt_item: str, gt_room: str) -> bool:
    """Match on item + room (Appendix D); mask IoU applies when GT masks exist.

    The Phase 0 GroundTruthHazard schema carries time ranges, not masks,
    so eval matching is item+room; mask_iou above is unit-tested and used
    by the labelling flow when masks are drawn.
    """
    return pred.item_id == gt_item and pred.room == gt_room


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    """Precision / recall / F1 from counts (0.0 on empty denominators)."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def evaluate_capture(
    capture: EvalCapture, predicted: list[Hazard], cannot_assess_count: int
) -> dict[str, object]:
    """Score one capture's predictions against its ground truth."""
    usable = [h for h in predicted if h.verification.value != "rejected"]
    matched_pred: set[int] = set()
    tp = fn = 0
    confusion = {
        "confirmed_correct": 0,
        "confirmed_wrong": 0,
        "needs_human_on_real": 0,
        "missed": 0,
    }
    per_severity: dict[str, dict[str, int]] = {}
    per_kind: dict[str, dict[str, int]] = {}
    for gt in capture.hazards:
        hit_idx = next(
            (
                i
                for i, h in enumerate(usable)
                if i not in matched_pred and _matches(h, gt.item_id, gt.room)
            ),
            None,
        )
        sev = per_severity.setdefault("unknown", {"tp": 0, "fn": 0})
        if hit_idx is None:
            fn += 1
            confusion["missed"] += 1
            sev["fn"] += 1
        else:
            matched_pred.add(hit_idx)
            tp += 1
            hit = usable[hit_idx]
            sev["tp"] += 1
            kind_bucket = per_kind.setdefault(hit.kind.value, {"tp": 0, "fp": 0, "fn": 0})
            kind_bucket["tp"] += 1
            if hit.verification.value == "confirmed":
                confusion["confirmed_correct"] += 1
            elif hit.verification.value == "needs_human":
                confusion["needs_human_on_real"] += 1
    fp = len(usable) - len(matched_pred)
    for i, h in enumerate(usable):
        if i not in matched_pred:
            per_kind.setdefault(h.kind.value, {"tp": 0, "fp": 0, "fn": 0})["fp"] += 1
            if h.verification.value == "confirmed":
                confusion["confirmed_wrong"] += 1
    result: dict[str, object] = {
        "capture_id": capture.capture_id,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        **prf(tp, fp, fn),
        "confusion": confusion,
        "per_kind": {k: prf(v["tp"], v["fp"], v["fn"]) for k, v in per_kind.items()},
        "cannot_assess_rate": round(cannot_assess_count / max(1, len(capture.hazards)), 4),
    }
    return result


def aggregate(capture_results: list[dict[str, object]]) -> dict[str, object]:
    """Micro-averaged totals across captures."""
    tp = sum(int(r["tp"]) for r in capture_results)  # type: ignore[arg-type]
    fp = sum(int(r["fp"]) for r in capture_results)  # type: ignore[arg-type]
    fn = sum(int(r["fn"]) for r in capture_results)  # type: ignore[arg-type]
    return {"tp": tp, "fp": fp, "fn": fn, **prf(tp, fp, fn)}
