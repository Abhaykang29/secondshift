"""Seed the recorded demo results (fixtures/demo_store) into the store.

The recorded reports were produced by the real Meta pipeline on
2026-11-03 and ship with only their evidence frames (already
person-blurred, recompressed) - no raw videos. Idempotent: records
and frames are added only when missing, so this is safe to run on
every `make demo` start ("loads them into a fresh store on first
run").

Usage: .venv/bin/python scripts/seed_demo.py [data_dir]
"""

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "fixtures" / "demo_store"


def main() -> int:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ.get("DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    fragment_path = FIXTURES / "store.json"
    if not fragment_path.exists():
        print("seed_demo: no fixtures/demo_store/store.json - nothing to seed")
        return 0
    fragment = json.loads(fragment_path.read_text())
    data_dir.mkdir(parents=True, exist_ok=True)
    store_path = data_dir / "store.json"
    store = json.loads(store_path.read_text()) if store_path.exists() else {}

    prefix = data_dir.as_posix()
    added = 0
    for key, value in fragment.items():
        if key in store:
            continue
        if key.startswith("keyframes:") and prefix != "data":
            for kf in value.get("keyframes", []):
                if str(kf.get("image_path", "")).startswith("data/"):
                    kf["image_path"] = prefix + kf["image_path"][len("data"):]
        store[key] = value
        added += 1
    if added:
        tmp = store_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(store))
        tmp.replace(store_path)

    files_root = FIXTURES / "files"
    copied = 0
    if files_root.exists():
        for src in sorted(files_root.rglob("*")):
            if not src.is_file():
                continue
            target = data_dir / src.relative_to(files_root)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, target)
                copied += 1
    print(f"seed_demo: {added} records, {copied} frames seeded into {data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
