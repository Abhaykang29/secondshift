"""Demo check: the on-stage demo paths must work offline, every time.

Two guarantees, both checked without any network or live spend:
1. scripts/run_demo.py - the scripted demo (parent home, baby home,
   re-check, watch alert, rule refusal) replays from its recorded
   cache; any missing response fails loudly.
2. The app's own demo flow in mock mode: create a check-up, run the
   demo-home scan, read a report with confirmed hazards, compile a
   rule - the exact buttons a presenter would tap if the live
   connection failed on stage.

Note (2026-10-30): replaying a REAL recorded scan through a fresh
upload is NOT bit-exact - person-blur output varies slightly between
runs, which changes image hashes and therefore cache keys. The real
runs' reports stay in the store and open in the app with no provider
calls at all; that is the real-footage fallback, and it needs no
replay. See docs/DEMO_SCRIPT.md (tech fallbacks).

Usage: python scripts/demo_check.py   (exit 0 = pass)
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    replay = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_demo.py")],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert replay.returncode == 0, f"run_demo replay failed:\n{replay.stdout}\n{replay.stderr}"
    assert "watch_alerts: 1" in replay.stdout, replay.stdout

    os.environ["PROVIDER"] = "mock"
    os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="secondshift-demo-")
    from fastapi.testclient import TestClient
    from secondshift.main import create_app

    client = TestClient(create_app())
    checkup = client.post(
        "/api/checkups",
        json={
            "pack_ids": ["falls_older_adults"],
            "home_label": "Demo home",
            "resident_label": "Demo home",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    )
    assert checkup.status_code == 200, checkup.text
    cid = checkup.json()["id"]
    scan = client.post(f"/api/checkups/{cid}/scan", json={})
    assert scan.status_code == 200, scan.text
    report = client.get(f"/api/reports/{cid}")
    assert report.status_code == 200, report.text
    hazards = report.json()["hazards"]
    confirmed = [h for h in hazards if h["verification"] == "confirmed"]
    assert confirmed, "demo report has no confirmed hazards"
    rule = client.post(
        "/api/rules/compile",
        json={"text": "Tell me if the stair gate is open for more than 30 seconds"},
    )
    assert rule.status_code == 200, rule.text
    print(
        f"demo-check PASS: scripted demo replays offline; app demo flow "
        f"produced {len(hazards)} hazards ({len(confirmed)} confirmed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
