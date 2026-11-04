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


def _make_checkup(fresh: TestClient) -> str:
    created = fresh.post(
        "/api/checkups",
        json={
            "resident_label": "Scan failure test",
            "consent": {"resident_informed": True, "no_private_moments": True},
            "pack_ids": ["fire_safety"],
        },
    )
    assert created.status_code == 200
    return str(created.json()["id"])


def test_scan_provider_failure_is_plain_never_500(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Regression (2026-11-04): a transient provider error right after
    frame extraction surfaced as a raw 500. A failed scan must return
    HTTP 200 with job_status failed and a plain, actionable message."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    fresh = TestClient(create_app(), raise_server_exceptions=False)
    checkup_id = _make_checkup(fresh)

    import secondshift.api.scan as scan_api

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("HTTP Error 429: Too Many Requests")

    monkeypatch.setattr(scan_api, "run_scan_job", boom)
    res = fresh.post(f"/api/checkups/{checkup_id}/scan", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["job_status"] == "failed"
    assert "rate limit" in body["error"]
    assert "500" not in body["error"]
    job = fresh.get(f"/api/jobs/{body['job_id']}")
    assert job.status_code == 200
    assert job.json()["status"] == "failed"
    assert job.json()["error"] == body["error"]


def test_scan_unexpected_failure_is_generic_plain_message(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Any other scan exception also becomes the generic plain
    message - never a raw 500, never exception text."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    fresh = TestClient(create_app(), raise_server_exceptions=False)
    checkup_id = _make_checkup(fresh)

    import secondshift.api.scan as scan_api

    def boom(*args: object, **kwargs: object) -> None:
        raise ValueError("sweep index out of range in module xyz")

    monkeypatch.setattr(scan_api, "run_scan_job", boom)
    res = fresh.post(f"/api/checkups/{checkup_id}/scan", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["job_status"] == "failed"
    assert body["error"].startswith("The check stopped partway through.")
    assert "xyz" not in body["error"]
