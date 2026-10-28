"""API tests: health is live, packs are real, stubs are honest 501s."""

from fastapi.testclient import TestClient
from secondshift.main import app

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


def test_stubbed_resource_is_an_honest_501() -> None:
    """Phase 0 stubs return 501, never fake data."""
    res = client.get("/api/checkups")
    assert res.status_code == 501


def test_costs_endpoint_starts_at_zero() -> None:
    """GET /api/costs starts empty."""
    res = client.get("/api/costs")
    assert res.status_code == 200
    assert res.json()["spent_usd"] == 0.0
