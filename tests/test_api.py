"""API tests: health is live, packs are real, stubs are honest 501s."""

from fastapi.testclient import TestClient
from secondshift.main import app, create_app

client = TestClient(app)


def test_health() -> None:
    """GET /api/health returns ok."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_packs_endpoint_lists_real_packs() -> None:
    """GET /api/packs lists the three shipped packs with item counts."""
    res = client.get("/api/packs")
    assert res.status_code == 200
    packs = {p["pack_id"]: p for p in res.json()["packs"]}
    assert packs["falls_older_adults"]["item_count"] == 16
    assert packs["babyproofing"]["item_count"] == 13


def test_unknown_resource_is_an_honest_404() -> None:
    """Unknown resources 404 - the API never invents data.

    (Every Phase 0 stub route has since been implemented for real.)
    """
    res = client.get("/api/definitely-not-a-route")
    assert res.status_code == 404


def test_checkups_list_is_implemented() -> None:
    """GET /api/checkups lists checkups (implemented in Phase 1)."""
    res = client.get("/api/checkups")
    assert res.status_code == 200
    assert "checkups" in res.json()


def test_costs_endpoint_starts_at_zero(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """GET /api/costs starts empty on a fresh data dir.

    Isolated since pass 2 Phase B: the ledger persists, so a repo data
    dir that has served live calls legitimately reports spend.
    """
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    fresh = TestClient(create_app())
    res = fresh.get("/api/costs")
    assert res.status_code == 200
    assert res.json()["spent_usd"] == 0.0
