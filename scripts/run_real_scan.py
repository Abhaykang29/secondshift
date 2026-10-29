"""First REAL pipeline run (Phase 7): one walkthrough through live Meta providers.

Usage: PROVIDER=meta CACHE_MODE=record .venv/bin/python scripts/run_real_scan.py VIDEO.mp4
Creates a checkup with consent, uploads the video, runs the scan job to
completion, and prints the report summary (hazards, SAM confirmations,
cost ledger total, wall time). Auth resolves via providers.meta.transport
(env key or vault surrogate) - the key is never printed.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from secondshift.main import create_app  # noqa: E402


def main() -> int:
    video = Path(sys.argv[1])
    started = time.time()
    client = TestClient(create_app())
    created = client.post(
        "/api/checkups",
        json={
            "pack_ids": ["falls_older_adults"],
            "resident_label": "Real-run test home",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    )
    if created.status_code not in (200, 201):
        print(f"create failed: {created.status_code} {created.text[:300]}")
        return 1
    checkup_id = created.json()["id"]
    with video.open("rb") as fh:
        uploaded = client.post(
            f"/api/checkups/{checkup_id}/captures",
            files={"file": (video.name, fh, "video/mp4")},
        )
    print(f"upload: {uploaded.status_code}")
    if uploaded.status_code not in (200, 201):
        print(uploaded.text[:300])
        return 1
    capture_id = uploaded.json().get("id")
    scan_started = time.time()
    scan = client.post(f"/api/checkups/{checkup_id}/scan", json={"capture_id": capture_id})
    print(f"scan: {scan.status_code} after {time.time() - scan_started:.0f}s")
    if scan.status_code != 200:
        print(scan.text[:600])
        return 1
    report = scan.json().get("report")
    elapsed = time.time() - started
    if report is None:
        print(f"scan response carried no report: {scan.text[:400]}")
        return 1
    hazards = report.get("hazards", [])
    print(f"\n=== REAL RUN REPORT ({video.name}) ===")
    print(f"wall time: {elapsed:.0f}s | hazards: {len(hazards)}")
    for hazard in hazards:
        print(
            f"  #{hazard.get('rank')} {hazard.get('item_id')} "
            f"[{hazard.get('verification_status')}] risk={hazard.get('risk_score')} "
            f"room={hazard.get('room')} - {hazard.get('evidence_summary', '')[:80]}"
        )
    print(f"rooms not assessable: {report.get('rooms_not_assessable')}")
    print(f"safety score: {report.get('safety_score')}")
    print(f"cost summary: {json.dumps(report.get('cost_summary'))}")
    Path("/tmp/real_report.json").write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
