"""Pass 2 Phase A tests: the truth pass - no fake surfaces remain."""

from fastapi.testclient import TestClient
from secondshift.main import create_app

client = TestClient(create_app())


def test_settings_report_provider_mode() -> None:
    """Settings expose provider_mode so the UI can banner mock mode."""
    res = client.get("/api/settings")
    assert res.status_code == 200
    assert res.json()["provider_mode"] == "mock"  # default provider is mock
    assert res.headers.get("x-provider-mode") == "mock"


def test_watch_simulate_is_named_simulation() -> None:
    """The scripted watch run lives at /simulate; /demo-run is gone."""
    res = client.post(
        "/api/watch/simulate",
        json={"rule_text": "Tell me if the baby gate is open for more than 30 seconds."},
    )
    assert res.status_code == 200
    assert client.post("/api/watch/demo-run", json={"rule_text": "x"}).status_code == 404


def test_eval_latest_labels_mock_source() -> None:
    """Eval payloads carry labels_source so the UI can hide mock runs."""
    res = client.get("/api/eval/latest")
    if res.status_code == 200:  # a run may not exist on a fresh checkout
        assert res.json()["labels_source"] in ("mock", "real")
