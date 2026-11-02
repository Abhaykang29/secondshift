"""Guided re-film (final pass, item 1): instruction generation,
the always_cannot_assess guard, and merge semantics
(CANNOT_TELL -> MET / -> NOT_MET / stays CANNOT_TELL)."""

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from secondshift.checklists.loader import load_all_packs  # noqa: E402
from secondshift.domain.enums import Verification  # noqa: E402
from secondshift.domain.hazards import (  # noqa: E402
    CannotAssess,
    Evidence,
    Hazard,
    RefilmInstruction,
    Report,
)
from secondshift.pipeline import refilm as refilm_mod  # noqa: E402
from secondshift.pipeline.scan import ScanOutput  # noqa: E402
from secondshift.providers.mock.vision import MockVisionReasoner  # noqa: E402

PACKS = load_all_packs()
FALLS = [PACKS["falls_older_adults"]]
CAR_SEAT = [PACKS["car_seat_check"]]


def _ca(item_id: str, reason: str = "not_filmed", detail: str = "not seen") -> CannotAssess:
    return CannotAssess(area=item_id, reason=reason, detail=detail)  # type: ignore[arg-type]


def _hazard(item_id: str, verification: Verification, risk: float = 50.0) -> Hazard:
    item = next(i for p in FALLS + CAR_SEAT for i in p.items if i.id == item_id)
    return Hazard(
        id=f"hz-{item_id.lower()}",
        checkup_id="chk-1",
        pack_id="falls_older_adults",
        item_id=item_id,
        kind=item.kind,
        room=item.rooms[0] if item.rooms else "bathroom",
        title=item.title,
        description="d",
        why_it_matters="w",
        severity=item.severity,
        verification=verification,
        verification_reason="r",
        evidence=Evidence(keyframe_ids=["kf-1"], timestamps=[1.0]),
        risk_score=risk,
    )


def _report(cannot: list[CannotAssess], hazards: list[Hazard] | None = None) -> Report:
    return Report(
        checkup_id="chk-1",
        generated_at=datetime.now(UTC),
        pack_ids=["falls_older_adults", "car_seat_check"],
        summary="s",
        fix_first=[],
        hazards=hazards or [],
        fixes=[],
        visualizations=[],
        routine_insights=[],
        cannot_assess=cannot,
        refilm_instructions=[
            RefilmInstruction(
                item_id=entry.area, room="bathroom", instruction="i", what_to_show="w"
            )
            for entry in cannot
        ],
        stats={},
        disclaimer="d",
    )


def test_instructions_skip_always_cannot_assess() -> None:
    cannot = [_ca("FALL-BATH-GRAB-MISSING"), _ca("SEAT-TIGHTNESS")]
    made = refilm_mod.generate_refilm_instructions(
        cannot, FALLS + CAR_SEAT, [], MockVisionReasoner()
    )
    assert [ins.item_id for ins in made] == ["FALL-BATH-GRAB-MISSING"]


def test_instruction_schema_word_caps() -> None:
    cannot = [_ca("FALL-BATH-GRAB-MISSING"), _ca("FALL-BATH-NONSLIP-MISSING")]
    made = refilm_mod.generate_refilm_instructions(cannot, FALLS, [], MockVisionReasoner())
    assert len(made) == 2
    for ins in made:
        assert len(ins.instruction.split()) <= 15
        assert len(ins.what_to_show.split()) <= 6
        assert ins.room == "bathroom"


def test_build_refilm_pack_only_refilmable_items() -> None:
    report = _report([_ca("FALL-BATH-GRAB-MISSING"), _ca("SEAT-TIGHTNESS")])
    pack = refilm_mod.build_refilm_pack(report, FALLS + CAR_SEAT)
    assert pack is not None
    assert [item.id for item in pack.items] == ["FALL-BATH-GRAB-MISSING"]
    only_fixed = _report([_ca("SEAT-TIGHTNESS")])
    assert refilm_mod.build_refilm_pack(only_fixed, FALLS + CAR_SEAT) is None


def test_merge_resolves_confirmed() -> None:
    previous = _report([_ca("FALL-BATH-GRAB-MISSING"), _ca("FALL-BATH-NONSLIP-MISSING")])
    output = ScanOutput(
        hazards=[_hazard("FALL-BATH-GRAB-MISSING", Verification.CONFIRMED, risk=80.0)],
        cannot_assess=[_ca("FALL-BATH-NONSLIP-MISSING")],
        routine_insights=[],
        fix_first=[],
        rooms_seen=["bathroom"],
    )
    merged = refilm_mod.merge_refilm(previous, output, FALLS + CAR_SEAT)
    resolved = [h for h in merged.hazards if h.item_id == "FALL-BATH-GRAB-MISSING"]
    assert len(resolved) == 1
    assert resolved[0].origin == "follow_up"
    assert resolved[0].verification is Verification.CONFIRMED
    assert [entry.area for entry in merged.cannot_assess] == ["FALL-BATH-NONSLIP-MISSING"]
    assert merged.stats["refilm_resolved"] == 1.0
    assert merged.stats["refilm_clips"] == 1.0
    assert [ins.item_id for ins in merged.refilm_instructions] == ["FALL-BATH-NONSLIP-MISSING"]
    assert any(fix.hazard_id == resolved[0].id for fix in merged.fixes)
    assert "Couldn\'t check 1 item" in merged.summary


def test_merge_resolves_rejected_as_not_met() -> None:
    previous = _report([_ca("FALL-BATH-NONSLIP-MISSING")])
    output = ScanOutput(
        hazards=[_hazard("FALL-BATH-NONSLIP-MISSING", Verification.REJECTED)],
        cannot_assess=[],
        routine_insights=[],
        fix_first=[],
        rooms_seen=["bathroom"],
    )
    merged = refilm_mod.merge_refilm(previous, output, FALLS + CAR_SEAT)
    assert merged.cannot_assess == []
    rejected = [h for h in merged.hazards if h.item_id == "FALL-BATH-NONSLIP-MISSING"]
    assert len(rejected) == 1 and rejected[0].origin == "follow_up"


def test_merge_stays_cannot_tell_with_new_reason() -> None:
    previous = _report([_ca("FALL-BATH-GRAB-MISSING", reason="not_filmed")])
    output = ScanOutput(
        hazards=[],
        cannot_assess=[_ca("FALL-BATH-GRAB-MISSING", reason="too_dark", detail="dark")],
        routine_insights=[],
        fix_first=[],
        rooms_seen=["bathroom"],
    )
    merged = refilm_mod.merge_refilm(previous, output, FALLS + CAR_SEAT)
    assert len(merged.cannot_assess) == 1
    assert merged.cannot_assess[0].reason == "too_dark"
    assert merged.stats["refilm_resolved"] == 0.0


@pytest.fixture(scope="module")
def synthetic_video(tmp_path_factory: pytest.TempPathFactory) -> str:
    out = tmp_path_factory.mktemp("refilm") / "synthetic.mp4"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "make_synthetic_video.py"), "--out", str(out)],
        check=True,
        capture_output=True,
    )
    return str(out)


def test_refilm_endpoint_404_without_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROVIDER", "mock")
    from fastapi.testclient import TestClient
    from secondshift.main import create_app

    client = TestClient(create_app())
    response = client.post(
        "/api/checkups/nope/refilm",
        files={"video": ("clip.mp4", b"not-a-video", "video/mp4")},
    )
    assert response.status_code == 404


def test_refilm_endpoint_merges(
    synthetic_video: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROVIDER", "mock")
    from fastapi.testclient import TestClient
    from secondshift.main import create_app

    app = create_app()
    previous = _report([_ca("FALL-BATH-GRAB-MISSING")])
    app.state.store.put("report", "chk-1", previous.model_dump(mode="json"))
    client = TestClient(app)
    with open(synthetic_video, "rb") as handle:
        response = client.post(
            "/api/checkups/chk-1/refilm",
            files={"video": ("followup.mp4", handle, "video/mp4")},
        )
    assert response.status_code == 200, response.text
    merged = response.json()
    # The mock sweep finds the grab-bar prompt deterministically, so
    # the item resolves end-to-end through the real endpoint: it
    # leaves cannot_assess and lands in hazards as a follow-up find.
    assert merged["stats"]["refilm_clips"] == 1.0
    assert merged["stats"]["refilm_resolved"] == 1.0
    assert merged["cannot_assess"] == []
    follow = [h for h in merged["hazards"] if h["item_id"] == "FALL-BATH-GRAB-MISSING"]
    assert len(follow) == 1 and follow[0]["origin"] == "follow_up"
    stored = app.state.store.get("report", "chk-1")
    assert stored is not None and stored["stats"]["refilm_clips"] == 1.0
