"""Phone mode (make phone): with SERVE_FRONTEND=1 the backend serves
the built frontend from the same origin, and client-side routes fall
back to index.html instead of 404ing. Skipped when no frontend build
exists (fresh clone before `npm run build`)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from secondshift.main import create_app

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@pytest.mark.skipif(not DIST.is_dir(), reason="frontend/dist not built")
def test_spa_served_same_origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SERVE_FRONTEND", "1")
    client = TestClient(create_app(), raise_server_exceptions=False)
    root = client.get("/")
    assert root.status_code == 200
    assert "text/html" in root.headers["content-type"]
    for route in ("/live", "/checkup/some-id/report", "/learn"):
        resp = client.get(route)
        assert resp.status_code == 200, route
        assert "text/html" in resp.headers["content-type"], route
    assert client.get("/api/health").status_code == 200
    missing = client.get("/api/definitely-not-a-route")
    assert missing.status_code == 404, "API misses must stay JSON 404s, not the SPA"
