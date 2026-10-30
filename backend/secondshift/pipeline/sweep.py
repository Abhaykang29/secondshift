"""SAM sweep - the second direction of the two-way check (2026-10-30).

Propose-then-verify only finds what the vision model happens to
mention, and its recall varies run to run. The sweep runs the other
direction for PRESENCE items: for every presence item whose rooms were
actually filmed, SAM segments the item's own prompts on the 3 sharpest
frames of each filmed room, and any plausible hit goes to the judge.
Items the propose path already confirmed (or sent to a human) in the
same room are skipped - the sweep exists to catch what propose missed
or wrongly rejected.

Budget: at most SWEEP_SAM_BUDGET SAM calls per scan, spent on
uncovered items first (deterministic order: item id, then room).
Provider errors degrade to "no hit" - the sweep can only add recall,
never break a scan.
Depends on: providers.base, domain models, checklists.loader,
pipeline.verify helpers (mask plausibility + evidence scoring).
"""

from concurrent.futures import ThreadPoolExecutor

from secondshift.checklists.loader import Pack, PackItem
from secondshift.domain.checkup import Keyframe
from secondshift.domain.enums import ItemKind, Severity, Verification
from secondshift.domain.hazards import Evidence, Hazard, Mask
from secondshift.pipeline.verify import _best_mask, _plausible
from secondshift.providers.base import ImageRef, JudgeRequest, Segmenter, VisionReasoner

SWEEP_SAM_BUDGET = 100
FRAMES_PER_ROOM = 3
_MIN_FRAME_GAP_S = 1.5

_STRENGTH = {
    Verification.CONFIRMED: 4,
    Verification.NEEDS_HUMAN: 3,
    Verification.REJECTED: 2,
    Verification.CANNOT_ASSESS: 1,
}


def best_frames_by_room(
    keyframes: list[Keyframe], per_room: int = FRAMES_PER_ROOM
) -> dict[str, list[Keyframe]]:
    """The sharpest usable frames per room label, spread in time."""
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
) -> list[tuple[Pack, PackItem, Keyframe]]:
    """Deterministic (pack item, frame) SAM calls within the budget.

    One call covers one item on one frame (all of the item's prompts go
    in that call). Uncovered presence items only, ordered by item id
    then room so the budget is spent the same way every run.
    """
    rooms_seen = sorted(frames_by_room)
    plan: list[tuple[Pack, PackItem, Keyframe]] = []
    calls = 0
    candidates: list[tuple[str, str, Pack, PackItem, Keyframe]] = []
    for pack in packs:
        for item in pack.items:
            if item.kind is not ItemKind.PRESENCE or not item.sam_prompts:
                continue
            for room in _item_rooms(item, rooms_seen):
                if (item.id, room) in covered:
                    continue
                for frame in frames_by_room[room]:
                    candidates.append((item.id, room, pack, item, frame))
    candidates.sort(key=lambda c: (c[0], c[1], c[4].t))
    for _item_id, _room, pack, item, frame in candidates:
        if calls >= budget:
            break
        plan.append((pack, item, frame))
        calls += 1
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
) -> list[Hazard]:
    """Run the sweep. Returns hazards for items with a plausible SAM hit."""
    frames_by_room = best_frames_by_room(keyframes)
    frames_by_room = {r: fs for r, fs in frames_by_room.items() if r in rooms_seen}
    plan = plan_sweep(packs, frames_by_room, covered, budget=budget)
    if not plan:
        return []

    def _segment(entry: tuple[Pack, PackItem, Keyframe]) -> tuple[Pack, PackItem, Keyframe, list[Mask]]:
        _pack, item, frame = entry
        try:
            masks = segmenter.segment(
                ImageRef(path=frame.image_path, keyframe_id=frame.id, t=frame.t),
                item.sam_prompts,
            )
        except Exception:
            masks = []
        return entry[0], item, frame, [m for m in masks if _plausible(m, min_mask_score)]

    with ThreadPoolExecutor(max_workers=min(8, len(plan))) as pool:
        results = list(pool.map(_segment, plan))

    hits: dict[tuple[str, str], tuple[Pack, PackItem, Keyframe, Mask]] = {}
    for pack, item, frame, masks in results:
        if not masks:
            continue
        best = _best_mask(masks)
        if best is None:
            continue
        key = (item.id, frame.room_guess or "")
        current = hits.get(key)
        if current is None or _mask_rank(best) > _mask_rank(current[3]):
            hits[key] = (pack, item, frame, best)

    hazards: list[Hazard] = []
    for offset, (_key, (pack, item, frame, mask)) in enumerate(sorted(hits.items())):
        room = frame.room_guess or "unknown"
        evidence = Evidence(
            keyframe_ids=[frame.id], timestamps=[frame.t], masks=[mask]
        )
        if verify_mode == "sam":
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
                reason = f"Found by SAM (box) on a room sweep; the judge could clearly see: {detail}."
            else:
                verification = Verification.NEEDS_HUMAN
                reason = f"SAM found it on a room sweep, but {detail} isn't clearly visible - a person should check."
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
                verification_reason=reason,
                evidence=evidence,
                risk_score=0.0,
            )
        )
    return hazards


def _mask_rank(mask: Mask) -> float:
    from secondshift.pipeline.verify import _evidence_score

    return _evidence_score(mask)
