"""Phase 3 tests: fix cards come only from the library, visualizations are
watermarked, reports render + share, the tracker persists."""

import os

os.environ.setdefault("DATA_DIR", "data")

from fastapi.testclient import TestClient
from secondshift.main import create_app

client = TestClient(create_app())


def _demo_report() -> tuple[str, dict]:  # type: ignore[type-arg]
    res = client.post(
        "/api/checkups",
        json={
            "pack_ids": ["falls_older_adults"],
            "resident_label": "Mom",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    )
    checkup_id = res.json()["id"]
    res = client.post(f"/api/checkups/{checkup_id}/scan", json={})
    assert res.status_code == 200, res.text
    return checkup_id, res.json()["report"]


def test_report_has_fix_cards_from_the_library_only() -> None:
    """Every fix card's chosen fix exists in the falls pack library."""
    from secondshift.checklists.loader import load_all_packs

    _, report = _demo_report()
    library_ids = {
        fix.id for pack in load_all_packs().values() for item in pack.items for fix in item.fixes
    }
    assert len(report["fixes"]) >= 8
    for card in report["fixes"]:
        assert card["chosen"]["id"] in library_ids
        assert 1 <= len(card["plain_language_steps"]) <= 5


def test_visualizations_are_watermarked_pngs() -> None:
    """Top hazards get visualizations with the exact watermark text."""
    checkup_id, report = _demo_report()
    assert len(report["visualizations"]) >= 1
    viz = report["visualizations"][0]
    assert viz["watermark"] == "Visualization - not a photo"
    res = client.get(f"/api/reports/{checkup_id}/image/{viz['image_path']}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"


def test_report_html_and_share_text() -> None:
    """HTML renders with the disclaimer; share text names the top fixes."""
    checkup_id, _ = _demo_report()
    html = client.get(f"/api/reports/{checkup_id}/html")
    assert html.status_code == 200
    assert "not a medical device" in html.text
    share = client.get(f"/api/reports/{checkup_id}/share").json()
    assert share["text"].startswith("Mom's home check-up:")
    assert share["whatsapp_url"].startswith("https://wa.me/?text=")


def test_fix_tracker_persists_status() -> None:
    """PATCH a fix to done; a fresh GET shows it done."""
    checkup_id, report = _demo_report()
    fix_id = report["fixes"][0]["id"]
    res = client.patch(
        f"/api/reports/{checkup_id}/fixes/{fix_id}",
        json={"status": "done", "note": "Dad did it Saturday"},
    )
    assert res.status_code == 200
    again = client.get(f"/api/reports/{checkup_id}").json()
    card = next(c for c in again["fixes"] if c["id"] == fix_id)
    assert card["status"] == "done" and card["note"] == "Dad did it Saturday"
