"""Partner footage filename mapping for the inbox watcher.

Bug fix under the final-pass freeze (2026-11-01): the footage hook in
data/inbox/ previously keyed on the build team's draft filenames
(falls_walkthrough.mp4, baby_walkthrough.mp4, ...). The partner
filming the official footage uses numbered names instead. This module
is the single source of truth for what each partner filename means;
the hook worker resolves every clip through it:

    .venv/bin/python -m secondshift.inbox_map 01_mom.mp4

Actions:
- "scan": run a normal check-up scan with pack_ids.
- "custom_check": compile checklist_lines into a custom checklist,
  store the compiled pack, and run a check with it.
- "refilm": a follow-up clip for the base_stem checkup; merge it into
  that checkup's report via the re-film endpoint (fills gaps in the
  SAME visit - never the re-check diff).
- "recheck": the same home filmed again after fixes; scan it and
  compare against the base_stem checkup's stored report. When
  checklist_lines is set, the base was a custom check - re-run with
  the same compiled custom pack.
- "live_check": run Live Check (watch engine over a FileSource) with
  the plain-English rule in `rule`.
- "unmapped": no partner mapping - never invent one.

Extensions .mp4 / .mov are accepted case-insensitively, and stems are
matched case-insensitively. Clips may be shot on glasses - any aspect
ratio, including vertical, is accepted as-is. Numbered clips 14 and
up that are not in the table get the default scan packs.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

VIDEO_EXTENSIONS = (".mp4", ".mov")

FALLS = "falls_older_adults"
BABYPROOFING = "babyproofing"
FIRE = "fire_safety"
QUAKE = "earthquake_ready"
PETS = "pet_safety"
HOME_SAFETY = "home_safety_inspection"
WORKPLACE = "workplace_safety"
CAR_SEAT = "car_seat_check"
MOSQUITO = "mosquito_breeding"

DOOR_RULE = "Tell me if the door is open for more than 30 seconds"
STOVE_RULE = "Tell me if the stove is on and nobody is in the kitchen for 1 minute."
TAP_RULE = "Tell me if the kitchen tap is running for more than 1 minute."

#: Custom checklists for the before/after pairs (compiled live on
#: 2026-11-02; see docs/LIVE_VERIFICATION.md for items and refusals).
TABLE_CHECKLIST_LINES = [
    "Table has no dishes or cups.",
    "All chairs are pushed in.",
]
#: The 16a table variant adds a floor line (3 items, no refusals).
TABLE_FLOOR_CHECKLIST_LINES = [
    "Table has no dishes or cups.",
    "All chairs are pushed in.",
    "Nothing on the floor around the table.",
]
KITCHEN_OFF_CHECKLIST_LINES = [
    "Stove burners are off.",
    "Taps are off.",
    "Windows are closed.",
    "Space heater or fan is off.",
]

#: Clips numbered 14+ default to the general home sweep.
DEFAULT_PACK_IDS = [FALLS, HOME_SAFETY, FIRE]


@dataclass(frozen=True)
class ClipPlan:
    """What the watcher should do with one inbox clip."""

    action: str  # scan | custom_check | refilm | recheck | live_check | unmapped
    pack_ids: list[str]
    stem: str = ""
    base_stem: str | None = None  # refilm/recheck: the clip this follows
    rule: str | None = None  # live_check: the plain-English rule
    false_alarm_test: bool = False  # clean-room clips: expect zero findings
    checklist_lines: list[str] | None = None  # custom_check / custom recheck
    post_refilm_instructions: bool = False  # surface the report's re-film list


def _scan(stem: str, pack_ids: list[str], *, false_alarm_test: bool = False) -> ClipPlan:
    return ClipPlan(
        action="scan",
        pack_ids=list(pack_ids),
        stem=stem,
        false_alarm_test=false_alarm_test,
    )


_KNOWN: dict[str, ClipPlan] = {
    "01_mom": _scan("01_mom", [FALLS, HOME_SAFETY]),
    "01b_refilm": ClipPlan(action="refilm", pack_ids=[], stem="01b_refilm", base_stem="01_mom"),
    "02_mom_fixed": ClipPlan(
        action="recheck",
        pack_ids=[FALLS, HOME_SAFETY],
        stem="02_mom_fixed",
        base_stem="01_mom",
    ),
    "03_baby": _scan("03_baby", [BABYPROOFING]),
    "04_pets": _scan("04_pets", [PETS]),
    "05_fire": _scan("05_fire", [FIRE]),
    "06_home_safety": _scan("06_home_safety", [HOME_SAFETY]),
    "07_quake": _scan("07_quake", [QUAKE]),
    "08_balcony": _scan("08_balcony", [MOSQUITO]),
    "09_clean_a": _scan("09_clean_a", [FALLS, BABYPROOFING, FIRE], false_alarm_test=True),
    "10_clean_b": _scan("10_clean_b", [FALLS, BABYPROOFING, FIRE], false_alarm_test=True),
    "11_door": ClipPlan(action="live_check", pack_ids=[], stem="11_door", rule=DOOR_RULE),
    "12_carseat": _scan("12_carseat", [CAR_SEAT]),
    "13_workplace": _scan("13_workplace", [WORKPLACE]),
    "15_stove": ClipPlan(action="live_check", pack_ids=[], stem="15_stove", rule=STOVE_RULE),
    "16a_table_before": ClipPlan(
        action="custom_check",
        pack_ids=[],
        stem="16a_table_before",
        checklist_lines=TABLE_FLOOR_CHECKLIST_LINES,
    ),
    "16b_table_after": ClipPlan(
        action="recheck",
        pack_ids=[],
        stem="16b_table_after",
        base_stem="16a_table_before",
        checklist_lines=TABLE_FLOOR_CHECKLIST_LINES,
    ),
    "17_tap": ClipPlan(action="live_check", pack_ids=[], stem="17_tap", rule=TAP_RULE),
    "18a_before": ClipPlan(
        action="custom_check",
        pack_ids=[],
        stem="18a_before",
        checklist_lines=TABLE_CHECKLIST_LINES,
    ),
    "18b_after": ClipPlan(
        action="recheck",
        pack_ids=[],
        stem="18b_after",
        base_stem="18a_before",
        checklist_lines=TABLE_CHECKLIST_LINES,
    ),
    "19a_before": ClipPlan(
        action="custom_check",
        pack_ids=[],
        stem="19a_before",
        checklist_lines=KITCHEN_OFF_CHECKLIST_LINES,
    ),
    "19b_after": ClipPlan(
        action="recheck",
        pack_ids=[],
        stem="19b_after",
        base_stem="19a_before",
        checklist_lines=KITCHEN_OFF_CHECKLIST_LINES,
    ),
    "20_vacuum": _scan("20_vacuum", [FALLS]),
    "21a": ClipPlan(
        action="scan",
        pack_ids=[FALLS, HOME_SAFETY],
        stem="21a",
        post_refilm_instructions=True,
    ),
    "21b": ClipPlan(action="refilm", pack_ids=[], stem="21b", base_stem="21a"),
}

_NUMBER_PREFIX = re.compile(r"^(\d+)")


def is_video_filename(filename: str) -> bool:
    """True for .mp4 / .mov files, extension case-insensitive."""
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS


def plan_for_filename(filename: str) -> ClipPlan:
    """Resolve a partner inbox filename to its processing plan.

    Accepts a bare name or a path. Unknown names, non-video files, and
    unknown numbered stems below 14 return action="unmapped" - the
    watcher reports those instead of guessing a mapping.
    """
    name = Path(filename).name
    if not is_video_filename(name):
        return ClipPlan(action="unmapped", pack_ids=[], stem=Path(name).stem.lower())
    stem = name[: -len(Path(name).suffix)].lower()
    known = _KNOWN.get(stem)
    if known is not None:
        return known
    match = _NUMBER_PREFIX.match(stem)
    if match and int(match.group(1)) >= 14:
        return _scan(stem, DEFAULT_PACK_IDS)
    return ClipPlan(action="unmapped", pack_ids=[], stem=stem)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve partner inbox filenames to watcher plans (JSON)."
    )
    parser.add_argument("filenames", nargs="+", help="clip filenames or paths")
    args = parser.parse_args(argv)
    plans = []
    for filename in args.filenames:
        entry = asdict(plan_for_filename(filename))
        entry["file"] = Path(filename).name
        plans.append(entry)
    print(json.dumps(plans, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
