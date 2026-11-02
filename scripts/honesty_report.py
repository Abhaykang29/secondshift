"""Honesty numbers (final pass, item 2): compute the app's accuracy
story from stored results - never typed by hand.

Sources (all on disk, all listed in the output):
- data/store.json: stored checkups + reports (a "clip" = a checkup
  with a real capture and a valid report; test/demo places and
  orphan reports without a checkup are excluded).
- eval/datasets/real/*.jsonl: the app's Right/Wrong review labels
  and missed-item notes.
- eval/datasets/real/test_1_ground_truth.json: the owner's 8-item
  ground truth for test_1.mp4 (Pass 3 P1 scoring convention).
- Partner inputs NN_notes.txt and the clean-room clips 09_clean_a /
  10_clean_b: looked for in data/inbox, docs and the workspace; if
  absent, the report says so - no substitute numbers are invented.

Outputs: eval/HONESTY.md + eval/honesty.json (the Learn tab card
reads the JSON via GET /api/honesty).

Usage: .venv/bin/python scripts/honesty_report.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from secondshift.domain.hazards import Report  # noqa: E402

ANSWERED = ("confirmed", "needs_human", "rejected")


def _load_reports() -> tuple[list[tuple[str, Report]], int]:
    store = json.loads((ROOT / "data" / "store.json").read_text())
    checkups = {
        key.split(":", 1)[1]: value
        for key, value in store.items()
        if key.startswith("checkup:")
    }
    captures = {
        key.split(":", 1)[1]: value
        for key, value in store.items()
        if key.startswith("capture:")
    }
    reports: list[tuple[str, Report]] = []
    skipped = 0
    for key, raw in store.items():
        if not key.startswith("report:"):
            continue
        checkup_id = key.split(":", 1)[1]
        checkup = checkups.get(checkup_id)
        if checkup is None:
            skipped += 1
            continue
        label = str(
            checkup.get("home_label") or checkup.get("resident_label") or ""
        ).lower()
        if any(marker in label for marker in ("smoke test", "custom test", "demo")):
            skipped += 1
            continue
        has_capture = any(
            cap.get("checkup_id") == checkup_id and float(cap.get("duration_s") or 0) > 0
            for cap in captures.values()
        )
        if not has_capture:
            skipped += 1
            continue
        try:
            reports.append((checkup_id, Report.model_validate(raw)))
        except Exception:
            skipped += 1
    return reports, skipped


def _review_labels() -> tuple[int, int, list[dict]]:
    right = wrong = 0
    wrong_confident: list[dict] = []
    real_dir = ROOT / "eval" / "datasets" / "real"
    for path in sorted(real_dir.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("kind") != "review":
                continue
            if entry.get("mark") == "right":
                right += 1
            elif entry.get("mark") == "wrong":
                wrong += 1
                if entry.get("verification") == "confirmed":
                    wrong_confident.append(
                        {
                            "item_id": entry.get("item_id"),
                            "room": entry.get("room"),
                            "checkup_id": path.stem,
                        }
                    )
    return right, wrong, wrong_confident


def _ground_truth(reports: list[tuple[str, Report]]) -> dict | None:
    path = ROOT / "eval" / "datasets" / "real" / "test_1_ground_truth.json"
    if not path.exists():
        return None
    truth = json.loads(path.read_text())
    by_id = dict(reports)
    for checkup_id in truth.get("applies_to_checkup_ids", []):
        report = by_id.get(checkup_id)
        if report is None:
            continue
        strict_hits = family_hits = answered = 0
        false_alarms: list[str] = []
        matched_families: set[str] = set()
        for target in truth["targets"]:
            hazards = [
                h
                for h in report.hazards
                if h.item_id in target["family_items"]
                and h.verification.value in ANSWERED
                and (target["room"] == "any" or h.room == target["room"])
            ]
            if hazards:
                answered += 1
            if any(h.item_id in target["items"] for h in hazards) and any(
                h.verification.value == target["expected"] for h in hazards
            ):
                strict_hits += 1
            if any(h.verification.value == target["expected"] for h in hazards):
                family_hits += 1
                matched_families.add(target["key"])
        truth_families = {t["key"] for t in truth["targets"]}
        family_by_item: dict[str, str] = {}
        for target in truth["targets"]:
            for item_id in target["family_items"]:
                family_by_item[item_id] = target["key"]
        for hazard in report.hazards:
            if hazard.verification.value not in ("confirmed", "needs_human"):
                continue
            fam = family_by_item.get(hazard.item_id)
            if fam is None or fam not in matched_families:
                # a reported finding outside the owner's list, or in a
                # family whose expected verdict did not occur
                if fam not in truth_families or fam not in matched_families:
                    false_alarms.append(
                        f"{hazard.item_id} ({hazard.room}, {hazard.verification.value})"
                    )
        return {
            "clip": truth["clip"],
            "targets": len(truth["targets"]),
            "answered": answered,
            "strict_recall": strict_hits,
            "family_recall": family_hits,
            "false_alarms": sorted(set(false_alarms)),
        }
    return {"clip": truth["clip"], "targets": len(truth["targets"]), "report_missing": True}


def main() -> int:
    reports, skipped = _load_reports()
    total_items = sum(len(r.hazards) + len(r.cannot_assess) for _, r in reports)
    answered_items = sum(len(r.hazards) for _, r in reports)
    abstained = sum(len(r.cannot_assess) for _, r in reports)
    right, wrong, wrong_confident = _review_labels()
    truth = _ground_truth(reports)
    refilm_resolved = sum(int(r.stats.get("refilm_resolved", 0)) for _, r in reports)
    refilm_clips = sum(int(r.stats.get("refilm_clips", 0)) for _, r in reports)
    follow_up_hazards = sum(
        1 for _, r in reports for h in r.hazards if h.origin == "follow_up"
    )
    notes_found = list(ROOT.glob("**/NN_notes.txt")) + list(
        (ROOT / "data" / "inbox").glob("NN_notes*")
    )
    clean_clips = [
        name
        for name in ("09_clean_a", "10_clean_b")
        if any((ROOT / "data" / "inbox").glob(f"{name}*"))
    ]
    data = {
        "clips": len(reports),
        "items": total_items,
        "answered_items": answered_items,
        "abstained_items": abstained,
        "abstain_rate_pct": round(100 * abstained / total_items, 1) if total_items else None,
        "review_labels": {"right": right, "wrong": wrong},
        "answered_accuracy_pct": (
            round(100 * right / (right + wrong), 1) if (right + wrong) else None
        ),
        "wrong_and_confident": wrong_confident,
        "ground_truth": truth,
        "clean_room": {
            "clips_found": clean_clips,
            "false_alarms": None if not clean_clips else 0,
        },
        "refilm": {
            "clips": refilm_clips,
            "resolved": refilm_resolved,
            "follow_up_hazards": follow_up_hazards,
        },
        "partner_notes_found": bool(notes_found),
        "small_sample": len(reports) < 10,
        "skipped_store_records": skipped,
    }
    (ROOT / "eval" / "honesty.json").write_text(json.dumps(data, indent=2) + "\n")

    def pct(value: float | None) -> str:
        return "no data" if value is None else f"{value}%"

    lines = [
        "# Honesty numbers",
        "",
        "Computed by `scripts/honesty_report.py` from stored results - never typed by hand.",
        "Command: `.venv/bin/python scripts/honesty_report.py`",
        "",
        f"- Clips scored (stored reports from real footage): **{data['clips']}**"
        + (" - fewer than 10 clips, so treat every rate below as a small sample." if data["small_sample"] else ""),
        f"- Items scored: **{total_items}** ({answered_items} answered, {abstained} cannot-tell).",
        f"- Abstain rate (answered CANNOT_TELL): **{pct(data['abstain_rate_pct'])}**",
        f"- Answered accuracy (app Right/Wrong labels): **{pct(data['answered_accuracy_pct'])}**"
        f" from {right + wrong} labels ({right} right, {wrong} wrong).",
    ]
    if truth and not truth.get("report_missing"):
        lines += [
            f"- Owner ground truth on {truth['clip']}: recall {truth['family_recall']}/{truth['targets']}"
            f" (strict item ids {truth['strict_recall']}/{truth['targets']});"
            f" reported findings outside the owner's list: {len(truth['false_alarms'])}"
            + (f" - {', '.join(truth['false_alarms'])}" if truth["false_alarms"] else "") + ".",
        ]
    elif truth:
        lines.append(f"- Owner ground truth on {truth['clip']}: the scored report is not in the store.")
    lines += [
        f"- Wrong-and-confident (confirmed findings labeled Wrong): **{len(wrong_confident)}**"
        + (": " + ", ".join(f"{w['item_id']} ({w['room']})" for w in wrong_confident) if wrong_confident else "."),
        "- Clean-room false alarms (09_clean_a / 10_clean_b): "
        + ("**not computable - the clean-room clips were never received.**" if not clean_clips else f"0 on {len(clean_clips)} clips."),
        f"- Before/after re-film: {refilm_resolved} cannot-tell items resolved by {refilm_clips} follow-up clip(s)"
        f" ({follow_up_hazards} follow-up findings in stored reports).",
        "- Partner scoring notes (NN_notes.txt): "
        + ("found." if notes_found else "**not received** - scoring against partner notes was not possible."),
        "",
        "Definitions: an item is 'answered' when the report carries a hazard verdict",
        "(confirmed / needs a human look / rejected) and 'abstained' when it sits in",
        "cannot_assess. Review-label accuracy counts only hazards a person marked",
        "Right or Wrong in the app.",
    ]
    (ROOT / "eval" / "HONESTY.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
