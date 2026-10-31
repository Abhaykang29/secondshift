"""Rewrite every stored report's summary with the plain two-sentence
template (demo cleanup, 2026-10-30). The summary is recomputed from
each report's own hazards / fix-first list / cannot-assess entries -
no facts change, only the prose."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondshift.domain.hazards import Report  # noqa: E402
from secondshift.pipeline.scan import plain_summary  # noqa: E402
from secondshift.storage.repository import Repository  # noqa: E402


def main() -> int:
    store = Repository("data/store.json")
    count = 0
    for key, raw in list(store._store.items()):
        if not key.startswith("report:"):
            continue
        try:
            report = Report.model_validate(raw)
        except Exception:
            continue  # not a real report record (test residue) - skip
        new_summary = plain_summary(
            report.hazards, report.cannot_assess, report.fix_first, report.pack_ids
        )
        if new_summary != report.summary:
            raw["summary"] = new_summary
            store.put("report", report.checkup_id, raw)
            count += 1
            print(f"{report.checkup_id[:8]}: {new_summary}")
    print(f"refreshed {count} report summaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
