"""Dedupe and rank (spec section 9.7) - deterministic, unit-tested.

risk_score = severity_weight x exposure (capped 2.0) x verification_factor
             x (0.5 + 0.5 x max(mask score, model confidence))
Exposure: x1.5 on the routine path, x1.3 in a pack high-risk zone,
x1.2 when a narration fact affects the hazard.
Depends on: domain models, checklists.loader.
"""

from secondshift.checklists.loader import Pack
from secondshift.domain.checkup import NarrationFact
from secondshift.domain.enums import Verification
from secondshift.domain.hazards import Hazard

_SEVERITY_WEIGHT = {1: 1.0, 2: 2.0, 3: 3.0}
_VERIFICATION_FACTOR = {Verification.CONFIRMED: 1.0, Verification.NEEDS_HUMAN: 0.6}
_NARRATION_TAGS: dict[str, list[str]] = {
    "night_path": ["FALL-PATH-NIGHT-LIGHT"],
    "bathroom": [],
    "stairs": [],
    "kitchen": [],
    "routine_path": ["FALL-FURNITURE-SUPPORT"],
}


def _iou(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def dedupe_hazards(
    hazards: list[Hazard], dedupe_keys: dict[str, str | None] | None = None
) -> list[Hazard]:
    """Merge duplicates: same item + room + (mask IoU > 0.3 or times < 4s apart).

    Pass 2 Phase C: cross-pack merge - two DIFFERENT items from
    different packs that share a dedupe_key (e.g. the falls rug and the
    home-from-hospital rug) and point at the same object in the same
    room merge into one hazard carrying both pack tags.
    """
    keys = dedupe_keys or {}
    kept: list[Hazard] = []
    for hazard in hazards:
        if not hazard.pack_tags:
            hazard.pack_tags = [hazard.pack_id]
        duplicate_of: Hazard | None = None
        for existing in kept:
            same_item = existing.item_id == hazard.item_id
            cross_pack = (
                existing.pack_id != hazard.pack_id
                and keys.get(existing.item_id) is not None
                and keys.get(existing.item_id) == keys.get(hazard.item_id)
            )
            if not (same_item or cross_pack) or existing.room != hazard.room:
                continue
            same_object = False
            if existing.evidence.masks and hazard.evidence.masks:
                same_object = (
                    _iou(existing.evidence.masks[0].bbox, hazard.evidence.masks[0].bbox) > 0.3
                )
            if not same_object and existing.evidence.timestamps and hazard.evidence.timestamps:
                same_object = (
                    abs(existing.evidence.timestamps[0] - hazard.evidence.timestamps[0]) < 4.0
                )
            if same_object:
                duplicate_of = existing
                break
        if duplicate_of is None:
            kept.append(hazard)
        else:
            for tag in hazard.pack_tags:
                if tag not in duplicate_of.pack_tags:
                    duplicate_of.pack_tags.append(tag)

            def _best(h: Hazard) -> float:
                return max((m.score for m in h.evidence.masks), default=0.0)

            if _best(hazard) > _best(duplicate_of):
                kept[kept.index(duplicate_of)] = hazard
    return kept


def _narration_boost(hazard: Hazard, facts: list[NarrationFact]) -> bool:
    for fact in facts:
        for tag in fact.affects:
            items = _NARRATION_TAGS.get(tag, [])
            if hazard.item_id in items:
                return True
            if tag == "night_path" and hazard.room == "hallway":
                return True
            if tag in ("bathroom", "stairs", "kitchen") and hazard.room == tag:
                return True
    return False


def rank_hazards(
    hazards: list[Hazard],
    packs: list[Pack],
    confidences: dict[str, float],
    narration_facts: list[NarrationFact],
) -> tuple[list[Hazard], list[str]]:
    """Score, sort and rank hazards; return (ranked, fix_first hazard ids)."""
    pack_by_id = {p.pack_id: p for p in packs}
    scored: list[Hazard] = []
    for hazard in hazards:
        if hazard.verification in (Verification.REJECTED, Verification.CANNOT_ASSESS):
            hazard.risk_score = 0.0
            scored.append(hazard)
            continue
        pack = pack_by_id.get(hazard.pack_id)
        exposure = 1.0
        if hazard.on_routine_path:
            exposure *= 1.5
        if pack and hazard.room in pack.high_risk_zones:
            exposure *= 1.3
        if _narration_boost(hazard, narration_facts):
            exposure *= 1.2
        exposure = min(exposure, 2.0)
        best_mask = max((m.score for m in hazard.evidence.masks), default=0.0)
        confidence = max(best_mask, confidences.get(hazard.item_id, 0.0))
        hazard.risk_score = round(
            _SEVERITY_WEIGHT[int(hazard.severity)]
            * exposure
            * _VERIFICATION_FACTOR[hazard.verification]
            * (0.5 + 0.5 * confidence),
            3,
        )
        scored.append(hazard)
    ranked = sorted(
        (h for h in scored if h.verification in _VERIFICATION_FACTOR),
        key=lambda h: (-h.risk_score, h.item_id),
    )
    for position, hazard in enumerate(ranked, start=1):
        hazard.rank = position
    fix_first = [h.id for h in ranked if h.verification is Verification.CONFIRMED][:5]
    if len(fix_first) < 5:
        fix_first += [h.id for h in ranked if h.verification is Verification.NEEDS_HUMAN][
            : 5 - len(fix_first)
        ]
    ordered = ranked + [h for h in scored if h.verification not in _VERIFICATION_FACTOR]
    return ordered, fix_first
