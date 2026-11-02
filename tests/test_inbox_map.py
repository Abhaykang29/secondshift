"""Partner filename mapping for the inbox watcher (freeze bug fix,
2026-11-01): every numbered partner clip resolves to the packs /
action the partner agreed, extensions and stems are case-insensitive,
and unknown names are unmapped rather than guessed."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from secondshift.checklists.loader import load_all_packs  # noqa: E402
from secondshift.inbox_map import (  # noqa: E402
    DEFAULT_PACK_IDS,
    DOOR_RULE,
    is_video_filename,
    plan_for_filename,
)

SCAN_CASES = {
    "01_mom": ["falls_older_adults", "home_safety_inspection"],
    "03_baby": ["babyproofing"],
    "04_pets": ["pet_safety"],
    "05_fire": ["fire_safety"],
    "06_home_safety": ["home_safety_inspection"],
    "07_quake": ["earthquake_ready"],
    "08_balcony": ["mosquito_breeding"],
    "12_carseat": ["car_seat_check"],
    "13_workplace": ["workplace_safety"],
}


@pytest.mark.parametrize("stem,pack_ids", sorted(SCAN_CASES.items()))
def test_scan_mappings(stem: str, pack_ids: list[str]) -> None:
    plan = plan_for_filename(f"{stem}.mp4")
    assert plan.action == "scan"
    assert plan.pack_ids == pack_ids
    assert plan.stem == stem
    assert plan.false_alarm_test is False


def test_refilm_maps_to_the_01_mom_checkup() -> None:
    plan = plan_for_filename("01b_refilm.mp4")
    assert plan.action == "refilm"
    assert plan.base_stem == "01_mom"
    assert plan.pack_ids == []


def test_recheck_maps_against_01_mom_with_its_packs() -> None:
    plan = plan_for_filename("02_mom_fixed.mp4")
    assert plan.action == "recheck"
    assert plan.base_stem == "01_mom"
    # the re-check scans with the same packs as the original 01_mom run
    assert plan.pack_ids == plan_for_filename("01_mom.mp4").pack_ids


@pytest.mark.parametrize("stem", ["09_clean_a", "10_clean_b"])
def test_clean_room_clips_are_false_alarm_tests(stem: str) -> None:
    plan = plan_for_filename(f"{stem}.mp4")
    assert plan.action == "scan"
    assert plan.pack_ids == ["falls_older_adults", "babyproofing", "fire_safety"]
    assert plan.false_alarm_test is True


def test_door_clip_is_a_live_check_with_the_agreed_rule() -> None:
    plan = plan_for_filename("11_door.mp4")
    assert plan.action == "live_check"
    assert plan.rule == DOOR_RULE
    assert plan.rule == "Tell me if the door is open for more than 30 seconds"


@pytest.mark.parametrize(
    "name", ["14_front.mp4", "15_garden.mov", "27_anything.MP4", "99_x.mp4"]
)
def test_numbered_14_and_up_get_the_default_scan(name: str) -> None:
    plan = plan_for_filename(name)
    assert plan.action == "scan"
    assert plan.pack_ids == DEFAULT_PACK_IDS
    assert plan.pack_ids == ["falls_older_adults", "home_safety_inspection", "fire_safety"]


@pytest.mark.parametrize(
    "name",
    ["01_MOM.MP4", "03_Baby.Mov", "11_DOOR.MOV", "01B_REFILM.Mp4", "09_CLEAN_A.mov"],
)
def test_matching_is_case_insensitive(name: str) -> None:
    lower = plan_for_filename(name.lower())
    upper = plan_for_filename(name)
    assert upper.action == lower.action
    assert upper.pack_ids == lower.pack_ids
    assert upper.base_stem == lower.base_stem
    assert upper.rule == lower.rule
    assert upper.action != "unmapped"


def test_paths_resolve_by_basename() -> None:
    plan = plan_for_filename("data/inbox/05_fire.MOV")
    assert plan.action == "scan"
    assert plan.pack_ids == ["fire_safety"]


@pytest.mark.parametrize(
    "name",
    [
        "test_1.mp4",  # the build smoke clip is not a partner clip
        "falls_walkthrough.mp4",  # retired build-team naming
        "01_unknown.mp4",  # unknown stem below 14: never guessed
        "NN_notes.txt",  # partner notes are not a clip
        "random.mov.bak",
    ],
)
def test_unmapped_names_are_reported_not_guessed(name: str) -> None:
    plan = plan_for_filename(name)
    assert plan.action == "unmapped"
    assert plan.pack_ids == []


@pytest.mark.parametrize(
    "name,expected",
    [
        ("a.mp4", True),
        ("a.MP4", True),
        ("a.mov", True),
        ("a.MOV", True),
        ("a.txt", False),
        ("a.mp4.bak", False),
    ],
)
def test_is_video_filename(name: str, expected: bool) -> None:
    assert is_video_filename(name) is expected


def test_every_mapped_pack_id_exists() -> None:
    packs = load_all_packs()
    stems = list(SCAN_CASES) + [
        "02_mom_fixed",
        "09_clean_a",
        "10_clean_b",
        "14_default",
    ]
    for stem in stems:
        for pack_id in plan_for_filename(f"{stem}.mp4").pack_ids:
            assert pack_id in packs, f"{stem} maps to unknown pack {pack_id}"
