"""Pack loading tests: packs are data, and the shipped packs must be valid."""

import pytest
from secondshift.checklists.loader import PACKS_DIR, load_all_packs, load_pack


def test_all_packs_load_and_validate() -> None:
    """Every shipped pack parses and validates."""
    packs = load_all_packs()
    assert set(packs) == {"falls_older_adults", "babyproofing", "fire_safety"}


def test_falls_pack_is_the_full_hero_pack() -> None:
    """The falls pack ships all 16 Appendix A.1 items, covering every kind."""
    pack = load_pack(PACKS_DIR / "falls_older_adults.yaml")
    assert len(pack.items) == 16
    kinds = {i.kind.value for i in pack.items}
    assert kinds == {"presence", "absence", "interaction", "measurement"}
    ids = {i.id for i in pack.items}
    assert "FALL-FLOOR-RUG" in ids and "FALL-BATH-GRAB-MISSING" in ids


def test_babyproofing_pack_is_the_full_second_pack() -> None:
    """The babyproofing pack ships all 13 Appendix A.2 items."""
    pack = load_pack(PACKS_DIR / "babyproofing.yaml")
    assert len(pack.items) == 13
    assert any(i.id == "BABY-STAIRS-NO-GATE" for i in pack.items)


def test_every_item_has_at_least_one_fix() -> None:
    """No hazard may ship without a fix from its pack library."""
    for pack in load_all_packs().values():
        for item in pack.items:
            assert item.fixes, f"{item.id} has no fixes"


def test_absence_items_name_a_safety_object() -> None:
    """Absence items are unverifiable without safety prompts."""
    for pack in load_all_packs().values():
        for item in pack.items:
            if item.kind.value == "absence":
                assert item.safety_prompts, f"{item.id} is absence without safety_prompts"


def test_bad_pack_is_rejected(tmp_path: object) -> None:
    """A pack with a duplicate item id must fail validation."""
    from pathlib import Path

    bad = Path(str(tmp_path)) / "bad.yaml"
    bad.write_text(
        "pack_id: bad\ntitle: Bad\naudience: x\nhigh_risk_zones: []\n"
        "severity_weights: {1: 1.0}\nitems:\n"
        "  - {id: X-ONE, title: t, kind: presence, rooms: [any], severity: 1,"
        " observable_evidence: e, sam_prompts: [a], fixes: [{id: f, title: t, how: h,"
        " difficulty: easy, cost_estimate: free}]}\n"
        "  - {id: X-ONE, title: t, kind: presence, rooms: [any], severity: 1,"
        " observable_evidence: e, sam_prompts: [a], fixes: [{id: f, title: t, how: h,"
        " difficulty: easy, cost_estimate: free}]}\n"
    )
    with pytest.raises(Exception):
        load_pack(bad)
