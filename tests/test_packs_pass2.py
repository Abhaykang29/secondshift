"""Pass 2 Phase C tests: six packs, sources rule, cross-pack dedupe."""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from secondshift.checklists.loader import load_all_packs, load_pack
from secondshift.domain.enums import ItemKind
from secondshift.domain.hazards import Evidence, Hazard, Severity, Verification
from secondshift.main import create_app
from secondshift.pipeline.rank import dedupe_hazards

PACKS_DIR = Path(__file__).parent.parent / "backend" / "secondshift" / "checklists" / "packs"

EXPECTED = {
    "falls_older_adults": 16,
    "babyproofing": 13,
    "fire_safety": 10,
    "earthquake_ready": 10,
    "pet_safety": 10,
    "home_from_hospital": 11,
    "mosquito_breeding": 8,
    "home_safety_inspection": 14,
    "workplace_safety": 10,
    "car_seat_check": 8,
}


def test_all_six_packs_load_with_target_counts() -> None:
    """All 6 packs load and validate with the appendix item counts."""
    packs = load_all_packs()
    assert {pid: len(p.items) for pid, p in packs.items()} == EXPECTED
    for pack in packs.values():
        assert pack.status == "approved"
        for item in pack.items:
            assert item.sources, f"{item.id} missing sources"


def test_approved_pack_without_sources_is_refused(tmp_path: Path) -> None:
    """The loader refuses an approved pack whose items lack sources."""
    raw = yaml.safe_load((PACKS_DIR / "pet_safety.yaml").read_text())
    raw["items"][0]["sources"] = []
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="without sources"):
        load_pack(bad)
    raw["status"] = "draft"
    bad.write_text(yaml.safe_dump(raw))
    assert load_pack(bad).status == "draft"  # drafts are exempt


def test_visual_prompts_on_visual_top_fixes() -> None:
    """Every top fix has a visualization prompt except the 2 documented nulls."""
    allowed_null = {
        "QUAKE-CABINET-NO-LATCH",
        "HOSP-DOOR-NARROW",
        "MOSQ-GUTTER-CLOGGED",
        "MOSQ-BIRDBATH-STANDING",
    }
    for pack in load_all_packs().values():
        for item in pack.items:
            if item.id in allowed_null:
                continue
            assert item.fixes[0].visualization_prompt, f"{item.id} top fix lacks a prompt"


def _hazard(pack_id: str, item_id: str, at: float) -> Hazard:
    return Hazard(
        id=f"hz-{item_id}",
        checkup_id="c1",
        pack_id=pack_id,
        item_id=item_id,
        kind=ItemKind.PRESENCE,
        room="hallway",
        title="t",
        description="d",
        why_it_matters="w",
        severity=Severity(3),
        verification=Verification.CONFIRMED,
        verification_reason="r",
        evidence=Evidence(keyframe_ids=["k1"], timestamps=[at]),
        risk_score=1.0,
    )


def test_multi_pack_rug_dedupes_into_one_hazard_with_two_tags() -> None:
    """The same rug in falls + home-from-hospital merges with both tags."""
    keys = {"FALL-FLOOR-RUG": "rug_on_path", "HOSP-RUGS-PATH": "rug_on_path"}
    merged = dedupe_hazards(
        [
            _hazard("falls_older_adults", "FALL-FLOOR-RUG", 10.0),
            _hazard("home_from_hospital", "HOSP-RUGS-PATH", 11.0),
        ],
        keys,
    )
    assert len(merged) == 1
    assert sorted(merged[0].pack_tags) == ["falls_older_adults", "home_from_hospital"]


def test_checkup_rejects_more_than_three_packs() -> None:
    """A check-up takes 1-3 packs; 4 is a 422."""
    client = TestClient(create_app())
    res = client.post(
        "/api/checkups",
        json={
            "pack_ids": ["falls_older_adults", "babyproofing", "fire_safety", "pet_safety"],
            "resident_label": "x",
            "consent": {"resident_informed": True, "no_private_moments": True},
        },
    )
    assert res.status_code == 422


def test_mosquito_water_items_require_a_human_unless_water_is_visible() -> None:
    """Water-dependent mosquito items carry the needs_human_unless flag."""
    pack = load_all_packs()["mosquito_breeding"]
    flagged = {i.id for i in pack.items if i.needs_human_unless}
    assert flagged == {
        "MOSQ-BUCKET-WATER",
        "MOSQ-PLANT-SAUCER",
        "MOSQ-GUTTER-CLOGGED",
        "MOSQ-TIRES-OUTDOORS",
        "MOSQ-BOTTLES-CANS",
        "MOSQ-TARP-POOLING",
    }
    assert load_all_packs()["pet_safety"].demo is True  # Pass 3 s3.4: pets return to the demo


class _Seg:
    """Stub segmenter: always finds a plausible mask."""

    def segment(self, image, prompts):  # type: ignore[no-untyped-def]
        from secondshift.domain.hazards import Mask

        return [
            Mask(keyframe_id=image.keyframe_id or "k", bbox=(0.1, 0.1, 0.5, 0.5),
                 score=0.9, prompt=p)
            for p in prompts
        ]

    def segment_video(self, frames, prompts):  # type: ignore[no-untyped-def]
        return {}


class _Judge:
    """Stub judge: the detail is NOT clearly visible."""

    def judge(self, req):  # type: ignore[no-untyped-def]
        from secondshift.providers.base import JudgeResponse

        return JudgeResponse(verification="needs_human", reason="cannot see the detail")


def test_mosquito_bucket_is_needs_human_even_when_sam_finds_it() -> None:
    """The water rule: SAM finds the bucket; only a human (or a judge
    that can clearly see water) can confirm the hazard."""
    from secondshift.domain.checkup import Keyframe
    from secondshift.domain.hazards import HazardProposal
    from secondshift.pipeline.verify import verify_proposals

    packs = [load_all_packs()["mosquito_breeding"]]
    proposal = HazardProposal(
        item_id="MOSQ-BUCKET-WATER", pack_id="mosquito_breeding", room="outdoors",
        description="Bucket outside", evidence_timestamps=[1.0],
        sam_prompts=["bucket"], safety_prompts=[], confidence=0.9,
        why_risky="Standing water breeds mosquitoes.",
    )
    frames = [Keyframe(id="k1", capture_id="cap", t=1.0, image_path="/dev/null",
                       sharpness=1.0, brightness=0.5, usable=True)]
    for mode in ("sam", "sam_plus_judge"):
        hazards, _ = verify_proposals(
            _Seg(), _Judge(), packs, [proposal], frames, [], "c1", verify_mode=mode
        )
        assert hazards[0].verification.value == "needs_human", mode
