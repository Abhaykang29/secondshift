"""Smoke test (2026-10-29): one REAL user video through the live pipeline.

Usage: PROVIDER=meta CACHE_MODE=record SECONDSHIFT_PHASE_TAG=pass2-smoke \
  .venv/bin/python scripts/run_smoke_test.py VIDEO.mp4 [pack,pack,...]

Drives the real API (checkup -> upload -> scan) so person blurring,
the prompt-backed pipeline and Muse Image visualizations all run as
in production. Prints the full outcome breakdown and writes the report
to /tmp/smoke_report.json. NOT official footage - a smoke test only.
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
    packs = (sys.argv[2].split(",") if len(sys.argv) > 2
             else ["falls_older_adults", "fire_safety", "pet_safety"])
    started = time.time()
    client = TestClient(create_app())
    created = client.post(
        "/api/checkups",
        json={
            "pack_ids": packs,
            "resident_label": "Smoke test home (test_1)",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    )
    if created.status_code not in (200, 201):
        print(f"create failed: {created.status_code} {created.text[:300]}")
        return 1
    checkup_id = created.json()["id"]
    print(f"checkup: {checkup_id} packs: {packs}")
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
    scan_s = time.time() - scan_started
    print(f"scan: {scan.status_code} after {scan_s:.0f}s")
    if scan.status_code != 200:
        print(scan.text[:800])
        return 1
    body = scan.json()
    report = body.get("report")
    elapsed = time.time() - started
    if report is None:
        print(f"no report: {json.dumps(body)[:400]}")
        return 1
    Path("/tmp/smoke_report.json").write_text(json.dumps(report, indent=2))
    print(f"\n=== SMOKE REPORT ({video.name}) ===")
    print(f"wall: {elapsed:.0f}s (scan {scan_s:.0f}s) | checkup {checkup_id}")
    print(f"summary: {report.get('summary')}")
    buckets: dict[str, list[dict]] = {}
    for hz in report.get("hazards", []):
        buckets.setdefault(hz["verification"], []).append(hz)
    for status in ("confirmed", "needs_human", "rejected"):
        for hz in buckets.get(status, []):
            print(f"  [{status}] #{hz.get('rank')} {hz['item_id']} ({hz['room']}) "
                  f"risk={hz.get('risk_score')} - {hz.get('verification_reason', '')[:110]}")
    for ca in report.get("cannot_assess", []):
        print(f"  [cannot_assess] {ca.get('area', '?')} - {ca.get('reason', '')[:110]}")
    viz = report.get("visualizations", [])
    print(f"visualizations: {len(viz)}")
    for v in viz:
        print(f"  viz {v['hazard_id']}: {v['image_path']} | prompt: {v['prompt_used'][:80]}")
    print(f"fixes: {len(report.get('fixes', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
