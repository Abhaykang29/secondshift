"""SAM sweep - the second direction of the two-way check (2026-10-30).

Propose-then-verify only finds what the vision model happens to
mention, and its recall varies run to run. The sweep runs the other
direction for PRESENCE items: for every presence item whose rooms were
actually filmed, SAM segments the item's own prompts, and any
plausible hit goes to the judge. Items the propose path already
confirmed (or sent to a human) in the same room are skipped.

Pass 3 P1 additions:
- Thin objects (thin_object: cords, towels, straps) are swept on
  TILED crops - 2x2 tiles plus a floor-band crop of the sharpest frame
  per room - with tile boxes mapped back to full-frame coordinates.
  Separate budget: THIN_SAM_BUDGET prompt-level calls.
- Proximity items (sweep_anchor_prompts, e.g. towels vs the stove):
  the sweep segments object and anchor prompts on the same frame and
  confirms only when a found object overlaps an anchor box or sits
  within 10% of frame width of it; a found-but-far object becomes a
  needs_human finding.

Budgets are counted in prompt-level SAM calls (the transport bills
one call per prompt per image): SWEEP_SAM_BUDGET for the main sweep,
THIN_SAM_BUDGET extra for tiles. Provider errors degrade to "no hit" -
the sweep can only add recall, never break a scan.
Depends on: providers.base, domain models, checklists.loader,
pipeline.verify helpers (mask plausibility + evidence scoring).
"""

import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from secondshift.checklists.loader import Pack, PackItem
from secondshift.domain.checkup import Keyframe
from secondshift.domain.enums import ItemKind, Severity, Verification
from secondshift.domain.hazards import Evidence, Hazard, Mask
from secondshift.pipeline.verify import _best_mask, _evidence_score, _plausible
from secondshift.providers.base import ImageRef, JudgeRequest, Segmenter, VisionReasoner

SWEEP_SAM_BUDGET = 100
THIN_SAM_BUDGET = 40
FRAMES_PER_ROOM = 3
_MIN_FRAME_GAP_S = 1.5
_PROXIMITY_GAP = 0.10  # normalized frame width

# Tiles in priority order: the floor band (bottom 40%) first - cords
# and mats live there - then the two bottom quadrants, then the top.
TILES: list[tuple[float, float, float, float]] = [
    (0.0, 0.6, 1.0, 1.0),
    (0.0, 0.5, 0.5, 1.0),
    (0.5, 0.5, 1.0, 1.0),
    (0.0, 0.0, 0.5, 0.5),
    (0.5, 0.0, 1.0, 0.5),
]

_STRENGTH = {
    Verification.CONFIRMED: 4,
    Verification.NEEDS_HUMAN: 3,
    Verification.REJECTED: 2,
    Verification.CANNOT_ASSESS: 1,
}


@dataclass
class _Call:
    pack: Pack
    item: PackItem
    frame: Keyframe
    tile: tuple[float, float, float, float] | None = None


def best_frames_by_room(
    keyframes: list[Keyframe], per_room: int = FRAMES_PER_ROOM
) -> dict[str, list[Keyframe]]:
    """The sharpest usable frames per room, spread in time."""
    by_room: dict[str, list[Keyframe]] = {}
    for kf in keyframes:
        if kf.room_guess and kf.usable and kf.image_path:
            by_room.setdefault(kf.room_guess, []).append(kf)
    chosen: dict[str, list[Keyframe]] = {}
    for room, frames in by_room.items():
        picked: list[Keyframe] = []
        for kf in sorted(frames, key=lambda f: -f.sharpness):
            if all(abs(kf.t - p.t) >= _MIN_FRAME_GAP_S for p in picked):
                picked.append(kf)
            if len(picked) >= per_room:
                break
        if len(picked) < per_room:  # gap rule too strict: fill by sharpness
            for kf in sorted(frames, key=lambda f: -f.sharpness):
                if kf not in picked:
                    picked.append(kf)
                if len(picked) >= per_room:
                    break
        chosen[room] = sorted(picked, key=lambda f: f.t)
    return chosen


def _item_rooms(item: PackItem, rooms_seen: list[str]) -> list[str]:
    if "any" in item.rooms:
        return list(rooms_seen)
    return [room for room in item.rooms if room in rooms_seen]


def plan_sweep(
    packs: list[Pack],
    frames_by_room: dict[str, list[Keyframe]],
    covered: set[tuple[str, str]],
    budget: int = SWEEP_SAM_BUDGET,
    thin_budget: int = THIN_SAM_BUDGET,
) -> list[_Call]:
    """Deterministic sweep plan within the prompt-level budgets.

    Normal items: the room frames (sharpest first in time order).
    Thin items: tiles of the single sharpest frame per room, charged
    to the separate thin budget. Rooms follow the order the frames
    were filmed (frames_by_room insertion order follows the keyframe
    list); items run in id order - the same spend every run.
    """
    plan: list[_Call] = []
    spent = 0
    thin_spent = 0
    items: list[tuple[Pack, PackItem]] = sorted(
        ((pack, item) for pack in packs for item in pack.items),
        key=lambda pi: pi[1].id,
    )
    for pack, item in items:
        if item.kind is not ItemKind.PRESENCE or not item.sam_prompts:
            continue
        rooms = [
            r for r in _item_rooms(item, list(frames_by_room)) if (item.id, r) not in covered
        ]
        if item.thin_object:
            # Round-robin across this item's rooms, tiles in priority
            # order, so one item with many rooms cannot starve the
            # others: every (item, room) gets its floor band first.
            room_frames = [
                (room, max(frames_by_room[room], key=lambda f: f.sharpness))
                for room in rooms
                if frames_by_room[room]
            ]
            for tile in TILES:
                for room, sharpest in room_frames:
                    cost = len(item.sam_prompts)
                    if thin_spent + cost > thin_budget:
                        break
                    plan.append(_Call(pack, item, sharpest, tile))
                    thin_spent += cost
        else:
            for room in rooms:
                for frame in frames_by_room[room]:
                    cost = len(item.sam_prompts) * (2 if item.sweep_anchor_prompts else 1)
                    if spent + cost > budget:
                        break
                    plan.append(_Call(pack, item, frame))
                    spent += cost
    return plan


def merge_sweep_hazards(
    hazards: list[Hazard], sweep_hazards: list[Hazard]
) -> list[Hazard]:
    """Fold sweep hazards into the propose-path hazards.

    Same item + same room: the stronger verdict wins (the sweep exists
    to overturn weak verdicts, never to duplicate a finding).
    """
    out = list(hazards)
    index = {(h.item_id, h.room): i for i, h in enumerate(out)}
    for swept in sweep_hazards:
        key = (swept.item_id, swept.room)
        if key not in index:
            index[key] = len(out)
            out.append(swept)
        else:
            existing = out[index[key]]
            if _STRENGTH[swept.verification] > _STRENGTH[existing.verification]:
                swept.id = existing.id
                out[index[key]] = swept
    return out


def _remap_mask(mask: Mask, tile: tuple[float, float, float, float]) -> Mask:
    tx0, ty0, tx1, ty1 = tile
    x0, y0, x1, y1 = mask.bbox
    return mask.model_copy(
        update={
            "bbox": (
                tx0 + x0 * (tx1 - tx0),
                ty0 + y0 * (ty1 - ty0),
                tx0 + x1 * (tx1 - tx0),
                ty0 + y1 * (ty1 - ty0),
            ),
            "polygon": None,
        }
    )


def _near(a: Mask, b: Mask) -> bool:
    """Overlap, or a horizontal gap within the proximity allowance."""
    ax0, ay0, ax1, ay1 = a.bbox
    bx0, by0, bx1, by1 = b.bbox
    if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
        return True
    dx = max(0.0, max(ax0 - bx1, bx0 - ax1))
    return dx <= _PROXIMITY_GAP


def sweep_presence(
    segmenter: Segmenter,
    judge: VisionReasoner,
    packs: list[Pack],
    keyframes: list[Keyframe],
    rooms_seen: list[str],
    covered: set[tuple[str, str]],
    checkup_id: str,
    start_idx: int,
    *,
    verify_mode: str = "sam_plus_judge",
    min_mask_score: float = 0.5,
    budget: int = SWEEP_SAM_BUDGET,
    thin_budget: int = THIN_SAM_BUDGET,
) -> list[Hazard]:
    """Run the sweep. Returns hazards for items with a plausible SAM hit."""
    frames_by_room = best_frames_by_room(keyframes)
    frames_by_room = {r: fs for r, fs in frames_by_room.items() if r in rooms_seen}
    plan = plan_sweep(packs, frames_by_room, covered, budget=budget, thin_budget=thin_budget)
    if not plan:
        return []

    tmp = Path(tempfile.mkdtemp(prefix="secondshift-tiles-"))

    def _crop(frame: Keyframe, tile: tuple[float, float, float, float]) -> str | None:
        try:
            from PIL import Image

            img = Image.open(frame.image_path)
            w, h = img.size
            box = (int(tile[0] * w), int(tile[1] * h), int(tile[2] * w), int(tile[3] * h))
            out = tmp / f"{frame.id}-{tile[0]}-{tile[1]}.jpg"
            img.convert("RGB").crop(box).save(out, quality=88)
            return str(out)
        except Exception:
            return None

    def _segment(call: _Call) -> tuple[_Call, list[Mask], list[Mask]]:
        item, frame = call.item, call.frame
        path = frame.image_path
        if call.tile is not None:
            cropped = _crop(frame, call.tile)
            if cropped is None:
                return call, [], []
            path = cropped
        ref = ImageRef(path=path, keyframe_id=frame.id, t=frame.t)
        try:
            masks = segmenter.segment(ref, item.sam_prompts)
        except Exception:
            masks = []
        if call.tile is not None:
            masks = [_remap_mask(m, call.tile) for m in masks]
        anchors: list[Mask] = []
        if item.sweep_anchor_prompts:
            try:
                anchors = segmenter.segment(ref, item.sweep_anchor_prompts)
            except Exception:
                anchors = []
            if call.tile is not None:
                anchors = [_remap_mask(m, call.tile) for m in anchors]
        plausible = [m for m in masks if _plausible(m, min_mask_score)]
        return call, plausible, anchors

    with ThreadPoolExecutor(max_workers=min(8, len(plan))) as pool:
        results = list(pool.map(_segment, plan))
    for child in tmp.iterdir():
        child.unlink(missing_ok=True)
    tmp.rmdir()

    # Group hits per (item, room). Proximity items track near/far apart.
    hits: dict[tuple[str, str], tuple[Pack, PackItem, Keyframe, Mask]] = {}
    far_hits: dict[tuple[str, str], tuple[Pack, PackItem, Keyframe, Mask]] = {}
    for call, masks, anchors in results:
        if not masks:
            continue
        item, frame = call.item, call.frame
        key = (item.id, frame.room_guess or "")
        best = _best_mask(masks)
        if best is None:
            continue
        if item.sweep_anchor_prompts:
            near = any(_near(m, a) for m in masks for a in anchors)
            target = hits if near else far_hits
            current = target.get(key)
            if current is None or _evidence_score(best) > _evidence_score(current[3]):
                target[key] = (call.pack, item, frame, best)
        else:
            current = hits.get(key)
            if current is None or _evidence_score(best) > _evidence_score(current[3]):
                hits[key] = (call.pack, item, frame, best)
    for key in list(hits):  # a near hit anywhere beats a far hit elsewhere
        far_hits.pop(key, None)

    hazards: list[Hazard] = []
    ordered = sorted(hits.items()) + sorted(far_hits.items())
    for offset, (key, (pack, item, frame, mask)) in enumerate(ordered):
        room = frame.room_guess or "unknown"
        evidence = Evidence(keyframe_ids=[frame.id], timestamps=[frame.t], masks=[mask])
        is_far = key in far_hits and key not in hits
        if is_far:
            verification = Verification.NEEDS_HUMAN
            reason = (
                "SAM found it on a room sweep, but not next to the "
                f"{item.sweep_anchor_prompts[0]} - a person should check "
                "whether it is a hazard."
            )
        elif verify_mode == "sam":
            verification = Verification.CONFIRMED
            reason = "Found by SAM (box) on a room sweep."
        elif item.needs_human_unless:
            detail = item.needs_human_unless
            verdict = judge.judge(
                JudgeRequest(
                    claim=f"{item.id}: is {detail} clearly visible?",
                    images=[ImageRef(path=frame.image_path, keyframe_id=frame.id)],
                    context=(
                        f"sam_found: true (room sweep); detail_check: {detail}. "
                        "Confirm ONLY if the detail itself is clearly visible."
                    ),
                )
            )
            if verdict.verification == "confirmed":
                verification = Verification.CONFIRMED
                reason = (
                    f"Found by SAM (box) on a room sweep; the judge could clearly see: {detail}."
                )
            else:
                verification = Verification.NEEDS_HUMAN
                reason = (
                    f"SAM found it on a room sweep, but {detail} isn't clearly "
                    "visible - a person should check."
                )
        else:
            verdict = judge.judge(
                JudgeRequest(
                    claim=f"{item.id}: {item.observable_evidence or item.title}",
                    images=[ImageRef(path=frame.image_path, keyframe_id=frame.id)],
                    context=(
                        "sam_found: true (room sweep - SAM located the object in "
                        "this frame). Confirm only if the hazard itself is "
                        "clearly present in the frame."
                    ),
                )
            )
            verification = Verification(verdict.verification)
            reason = (
                f"Found by SAM (box) on a room sweep. {verdict.reason}"
                if verification is Verification.CONFIRMED
                else verdict.reason
            )
        hazards.append(
            Hazard(
                id=f"hz-{start_idx + offset:03d}-{item.id.lower()}",
                checkup_id=checkup_id,
                pack_id=pack.pack_id,
                item_id=item.id,
                kind=item.kind,
                room=room,
                title=item.title,
                description=item.observable_evidence or item.title,
                why_it_matters=item.observable_evidence or item.title,
                severity=Severity(item.severity),
                verification=verification,
                evidence=evidence,
                verification_reason=reason,
                risk_score=0.0,
            )
        )
    return hazards
