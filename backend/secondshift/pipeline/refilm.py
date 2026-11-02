"""Guided re-film (final pass, item 1): turn CANNOT_TELL items into
a short follow-up filming task, then merge the follow-up clip's
verdicts into the SAME report.

Re-film is not re-check: re-check compares a LATER visit against
this one (diff_scans); re-film fills the gaps of THIS visit - the
report keeps its identity, resolved items change their answer in
place and carry origin="follow_up" plus their own evidence frame.

Instruction generation: one Spark call per room (prompts/
refilm_instruction.md, reasoning low), inputs = the item, its
cannot-tell reason and the room's sharpest keyframe when one exists.
Items a camera can never settle (PackItem.always_cannot_assess,
e.g. car-seat tightness) never get instructions - their stored
explanation stands.
"""

import json
from typing import TYPE_CHECKING

from secondshift.checklists.loader import Pack, PackItem
from secondshift.domain.enums import Verification
from secondshift.domain.hazards import CannotAssess, RefilmInstruction, Report
from secondshift.pipeline.fixes import build_fix_cards
from secondshift.pipeline.scan import ScanOutput, plain_summary
from secondshift.providers.base import ImageRef

if TYPE_CHECKING:
    from secondshift.domain.checkup import Keyframe


def refilmable_items(
    cannot_assess: list[CannotAssess], packs: list[Pack]
) -> dict[str, PackItem]:
    """The cannot-assess entries that a follow-up clip could settle:
    entries whose area names a known pack item, minus the items no
    camera can ever assess."""
    items = {item.id: item for pack in packs for item in pack.items}
    out: dict[str, PackItem] = {}
    for entry in cannot_assess:
        item = items.get(entry.area)
        if item is None or item.always_cannot_assess:
            continue
        out[item.id] = item
    return out


def build_refilm_pack(previous: Report, packs: list[Pack]) -> Pack | None:
    """A checklist containing ONLY the previous report's refilmable
    cannot-tell items. None when there is nothing to re-film."""
    items = refilmable_items(previous.cannot_assess, packs)
    if not items:
        return None
    return Pack(
        status="draft",
        pack_id=f"refilm-{previous.checkup_id[:8]}",
        title="Re-film checks",
        audience="Follow-up clip: only the items the first walkthrough could not settle.",
        high_risk_zones=[],
        severity_weights={1: 1.0, 2: 1.0, 3: 1.0},
        items=list(items.values()),
    )


def _item_room(item: PackItem) -> str:
    return item.rooms[0] if item.rooms else "unlabeled area"


def _nearest_keyframe(keyframes: "list[Keyframe]", room: str) -> "Keyframe | None":
    """The sharpest usable keyframe labelled with this room."""
    candidates = [
        kf for kf in keyframes if kf.room_guess == room and kf.usable and kf.image_path
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda kf: kf.sharpness)


def generate_refilm_instructions(
    cannot_assess: list[CannotAssess],
    packs: list[Pack],
    keyframes: "list[Keyframe]",
    vision: object | None,
) -> list[RefilmInstruction]:
    """One instruction per refilmable cannot-tell item, grouped by
    room for the model call, ordered by risk (item severity) in the
    result. Provider failure for a room leaves those items without
    instructions rather than inventing any."""
    if vision is None:
        return []
    targets = refilmable_items(cannot_assess, packs)
    if not targets:
        return []
    entries = {entry.area: entry for entry in cannot_assess}
    by_room: dict[str, list[PackItem]] = {}
    for item in targets.values():
        by_room.setdefault(_item_room(item), []).append(item)
    made: dict[str, RefilmInstruction] = {}
    for room, room_items in sorted(by_room.items()):
        payload = json.dumps(
            [
                {
                    "item_id": item.id,
                    "title": item.title,
                    "reason": (
                        f"{entries[item.id].reason}: {entries[item.id].detail}"
                        if item.id in entries
                        else ""
                    ),
                }
                for item in room_items
            ]
        )
        keyframe = _nearest_keyframe(keyframes, room)
        image = (
            ImageRef(path=keyframe.image_path, keyframe_id=keyframe.id, t=keyframe.t)
            if keyframe is not None
            else None
        )
        try:
            results = vision.refilm_instructions(payload, room, image)  # type: ignore[attr-defined]
        except Exception:
            results = None
        if not results:
            continue
        wanted = {item.id for item in room_items}
        for entry in results:
            item_id = str(entry.get("item_id", ""))
            if item_id not in wanted or item_id in made:
                continue
            made[item_id] = RefilmInstruction(
                item_id=item_id,
                room=room,
                instruction=str(entry.get("instruction", "")),
                what_to_show=str(entry.get("what_to_show", "")),
            )
    return sorted(
        made.values(),
        key=lambda ins: (-targets[ins.item_id].severity, ins.room, ins.item_id),
    )


def merge_refilm(
    previous: Report, refilm_output: ScanOutput, packs: list[Pack]
) -> Report:
    """Merge a follow-up clip's scan into the previous report.

    - A cannot-tell item the clip settles (a hazard of any verdict)
      leaves cannot_assess and enters hazards with origin follow_up.
    - A cannot-tell item still unseen stays, with the NEW reason.
    - Everything else - hazards, fixes, visualizations, insights -
      is carried over untouched; fix cards are built only for the
      newly resolved hazards. Ranking, fix-first and the two-
      sentence summary are recomputed over the merged set.
    """
    targets = {entry.area for entry in previous.cannot_assess}
    resolved = {
        hazard.item_id: hazard
        for hazard in refilm_output.hazards
        if hazard.item_id in targets
    }
    # The follow-up scan ran under a temporary checklist: give its
    # hazards their original pack identity and collision-free ids
    # (scan hazard ids are per-scan sequential - hz-000-... would
    # clash with the original report's ids).
    pack_by_item = {
        item.id: pack.pack_id for pack in packs for item in pack.items
    }
    existing_ids = {h.id for h in previous.hazards}
    for hazard in resolved.values():
        hazard.pack_id = pack_by_item.get(hazard.item_id, hazard.pack_id)
        hazard.pack_tags = [
            tag for tag in hazard.pack_tags if not tag.startswith("refilm-")
        ]
        if hazard.pack_id not in hazard.pack_tags:
            hazard.pack_tags.append(hazard.pack_id)
        if hazard.id in existing_ids:
            hazard.id = f"rf-{hazard.id}"
    still = {entry.area: entry for entry in refilm_output.cannot_assess}
    new_hazards = list(previous.hazards)
    new_cannot: list[CannotAssess] = []
    resolved_count = 0
    for entry in previous.cannot_assess:
        found = resolved.get(entry.area)
        if found is not None:
            found.origin = "follow_up"
            found.checkup_id = previous.checkup_id
            new_hazards.append(found)
            resolved_count += 1
        elif entry.area in still:
            new_cannot.append(still[entry.area])
        else:
            new_cannot.append(entry)
    # Re-rank: confirmed / needs-human by risk score, ranks 1..N.
    ranked = sorted(
        (
            h
            for h in new_hazards
            if h.verification in (Verification.CONFIRMED, Verification.NEEDS_HUMAN)
        ),
        key=lambda h: -h.risk_score,
    )
    for position, hazard in enumerate(ranked, start=1):
        hazard.rank = position
    for hazard in new_hazards:
        if hazard.verification not in (Verification.CONFIRMED, Verification.NEEDS_HUMAN):
            hazard.rank = None
    fix_first = [
        h.id
        for h in sorted(
            (h for h in new_hazards if h.verification is Verification.CONFIRMED),
            key=lambda h: -h.risk_score,
        )
    ][:5]
    new_fixes = build_fix_cards(
        [h for h in new_hazards if h.origin == "follow_up"], packs, vision=None
    )
    stats = dict(previous.stats)
    stats["refilm_resolved"] = float(stats.get("refilm_resolved", 0) + resolved_count)
    stats["refilm_clips"] = float(stats.get("refilm_clips", 0) + 1)
    still_ids = {entry.area for entry in new_cannot}
    return Report(
        checkup_id=previous.checkup_id,
        generated_at=previous.generated_at,
        pack_ids=previous.pack_ids,
        summary=plain_summary(new_hazards, new_cannot, fix_first, previous.pack_ids),
        fix_first=fix_first,
        hazards=new_hazards,
        fixes=list(previous.fixes) + new_fixes,
        visualizations=previous.visualizations,
        routine_insights=previous.routine_insights,
        cannot_assess=new_cannot,
        refilm_instructions=[
            ins for ins in previous.refilm_instructions if ins.item_id in still_ids
        ],
        stats=stats,
        disclaimer=previous.disclaimer,
    )
