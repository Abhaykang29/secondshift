"""Pass 3 P3 backend: review labels + homes (places) APIs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from secondshift.api import reviews as reviews_mod  # noqa: E402
from secondshift.main import create_app  # noqa: E402


def _client_with_report(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(reviews_mod, "_LABELS_DIR", tmp_path / "labels")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    app = create_app()
    store = app.state.store
    store.put(
        "checkup",
        "chk-1",
        {
            "id": "chk-1",
            "home_label": "Mom's home",
            "resident_label": "Mom",
            "pack_ids": ["falls_older_adults"],
            "created_at": "2026-10-30T12:00:00+00:00",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    )
    store.put(
        "report",
        "chk-1",
        {
            "checkup_id": "chk-1",
            "hazards": [
                {"id": "hz-1", "item_id": "FALL-FLOOR-CORD", "room": "living",
                 "verification": "confirmed"}
            ],
            "fixes": [{"id": "f1", "status": "todo"}],
        },
    )
    return TestClient(app)


def test_review_labels_roundtrip(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client_with_report(tmp_path, monkeypatch)
    r = client.post("/api/checkups/chk-1/reviews", json={"hazard_id": "hz-1", "mark": "right"})
    assert r.status_code == 200 and r.json()["total_labels"] == 1
    r = client.post(
        "/api/checkups/chk-1/missed",
        json={"item_id": "FALL-FLOOR-RUG", "room": "kitchen", "timestamp_s": 12.0},
    )
    assert r.status_code == 200 and r.json()["total_labels"] == 2
    summary = client.get("/api/reviews/summary").json()
    assert summary == {"total_labels": 2, "verdicts": 1, "missed": 1, "checkups": 1}
    labels = client.get("/api/checkups/chk-1/reviews").json()["labels"]
    verdict = next(e for e in labels if e["type"] == "verdict")
    assert verdict["item_id"] == "FALL-FLOOR-CORD"  # stamped from the report
    manifest = (tmp_path / "labels" / "manifest.json").read_text()
    assert '"labels": 2' in manifest


def test_homes_list_and_delete(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client_with_report(tmp_path, monkeypatch)
    homes = client.get("/api/homes").json()["homes"]
    assert len(homes) == 1
    home = homes[0]
    assert home["label"] == "Mom's home"
    assert home["open_fixes"] == 1 and home["open_findings"] == 1
    assert home["recheck_due"].startswith("2026-11-29")
    r = client.delete("/api/homes/Mom's home")
    assert r.status_code == 200 and r.json()["deleted_checkups"] == 1
    assert client.get("/api/homes").json()["homes"] == []
    assert client.get("/api/reports/chk-1").status_code == 404
