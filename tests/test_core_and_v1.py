"""Pass 3 P4: core/ boundary + engine API + custom checklist flow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

CORE_DIR = Path(__file__).parent.parent / "backend" / "secondshift" / "core"


def test_core_imports_no_app_layer() -> None:
    """The engine may not import the app layer or UI-facing modules."""
    import ast

    offenders = []
    for path in CORE_DIR.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                if module.startswith(("secondshift.api", "secondshift.main", "fastapi")):
                    offenders.append(f"{path.name}: {module}")
    assert offenders == []


def test_compile_checklist_packs_and_custom() -> None:
    from secondshift.config import Settings
    from secondshift.core import compile_checklist
    from secondshift.providers.registry import build_providers

    packs = compile_checklist(["falls_older_adults", "fire_safety"])
    assert packs.source == "packs" and len(packs.pack.items) == 26
    vision = build_providers(Settings()).vision
    custom = compile_checklist(
        ["loose cords across the floor", "the extinguisher is bolted down tight"],
        vision=vision,
    )
    assert custom.source == "custom"
    assert custom.pack.status == "draft"
    assert [i.id for i in custom.pack.items] == ["CUSTOM-01"]
    assert len(custom.refusals) == 1  # tightness/bolted = hands-on, refused


def _v1_client(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    from secondshift.main import create_app

    return TestClient(create_app())


def test_v1_auth_rate_limit_and_rules(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _v1_client(tmp_path, monkeypatch)
    assert client.post("/v1/rules/compile", json={"sentence": "x"}).status_code == 401
    ok = client.post(
        "/v1/rules/compile",
        json={"sentence": "Tell me if the stair gate is open for more than 30 seconds"},
        headers={"X-API-Key": "local-dev-key"},
    )
    assert ok.status_code == 200
    for _ in range(30):  # the 31st request inside a minute is limited
        last = client.post(
            "/v1/rules/compile",
            json={"sentence": "Tell me if the gate is open"},
            headers={"X-API-Key": "local-dev-key"},
        )
    assert last.status_code == 429


def test_custom_checklist_api_roundtrip(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    from secondshift.main import create_app

    client = TestClient(create_app())
    too_few = client.post("/api/custom-checklists", json={"lines": ["only one"]})
    assert too_few.status_code == 422
    r = client.post(
        "/api/custom-checklists",
        json={
            "lines": [
                "loose cords across the walkway",
                "boxes stacked above shoulder height",
                "fire extinguisher mounted by the exit",
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["label"] == "Custom checklist - not reviewed by an expert"
    assert len(body["items"]) == 3
    got = client.get(f"/api/custom-checklists/{body['checklist_id']}")
    assert got.status_code == 200
