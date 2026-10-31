"""Demo reset: delete the TEST places (and all their data) so the
Homes tab shows only real places before demo recording.

Test places are checkups whose place label contains "Smoke test",
"Real-run test", "Custom test" or "Replay demo" (case-insensitive) - labels the
build's own verification runs used. Everything else is untouched.
Deletion mirrors DELETE /api/homes/{label}: checkups, reports, jobs,
rechecks, captures, keyframes, audio and the files on disk.

Usage: python scripts/demo_reset.py [--dry-run]
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondshift.storage.repository import Repository  # noqa: E402

TEST_MARKERS = ("smoke test", "real-run test", "custom test", "replay demo")


def place_label(raw: dict) -> str:  # type: ignore[type-arg]
    return str(raw.get("home_label") or raw.get("resident_label") or "Home")


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    store = Repository("data/store.json")
    targets: dict[str, list[dict]] = {}  # type: ignore[type-arg]
    remaining: set[str] = set()
    for raw in store.list("checkup"):
        label = place_label(raw)
        if any(marker in label.lower() for marker in TEST_MARKERS):
            targets.setdefault(label, []).append(raw)
        else:
            remaining.add(label)
    if not targets:
        print("demo-reset: no test places found")
    for label, checkups in sorted(targets.items()):
        print(f"{'would delete' if dry_run else 'deleting'} place: {label} ({len(checkups)} checkup(s))")
        if dry_run:
            continue
        for raw in checkups:
            checkup_id = str(raw.get("id"))
            for capture in store.list("capture"):
                if str(capture.get("checkup_id")) == checkup_id:
                    capture_id = str(capture.get("id"))
                    store.delete("capture", capture_id)
                    store.delete("keyframes", capture_id)
                    store.delete("audio", capture_id)
                    shutil.rmtree(Path("data") / capture_id, ignore_errors=True)
            for kind in ("checkup", "report", "job", "recheck"):
                store.delete(kind, checkup_id)
            shutil.rmtree(Path("data") / checkup_id, ignore_errors=True)
    print(f"places remaining: {sorted(remaining) if remaining else '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
