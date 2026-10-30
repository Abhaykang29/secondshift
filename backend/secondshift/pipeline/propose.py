"""Propose hazards (spec section 9.4).

Builds the pack-items request, calls the VisionReasoner in batches of
PROPOSE_BATCH keyframes in order, drops unknown item_ids, and dedupes
across batches. Output must validate as HazardProposal (the provider
contract guarantees it).

Smoke-test fixes (2026-10-29):
- Batches run in parallel (order preserved); the previous-findings
  summary is a de-duplication hint only, so parallel batches pass an
  empty summary and de-duplication happens here, deterministically.
- Every keyframe gets ONE room label (room_guess): from the propose
  response's per-image labels when present, else one classify_room
  call per unlabeled keyframe. That label is the only room label the
  rest of the pipeline uses.
- Evidence timestamps are never defaulted. Model timestamps are
  snapped to the batch keyframe they land on; a proposal whose
  timestamps are missing or do not land on any frame in its own batch
  keeps NO timestamps and instead carries the batch's keyframe ids as
  provenance (source_keyframe_ids) for the verifier to search.
Depends on: providers.base, checklists.loader, domain models.
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import yaml

from secondshift.checklists.loader import Pack
from secondshift.domain.checkup import Keyframe, Measurement, NarrationFact
from secondshift.domain.enums import Verification
from secondshift.domain.hazards import CannotAssess, Hazard, HazardProposal
from secondshift.providers.base import (
    ImageRef,
    ProposeRequest,
    ProposeResponse,
    VisionReasoner,
)

# How close a model timestamp must land to a batch keyframe (seconds)
# to count as pointing at that frame. Model timestamps are often whole
# seconds while keyframes sit on half-second marks.
_TIMESTAMP_TOLERANCE_S = 1.0

_ROOM_ALIASES = {
    "living_room": "living",
    "livingroom": "living",
    "bath": "bathroom",
    "bed": "bedroom",
    "hall": "hallway",
    "entrance": "entry",
    "ceiling": "ceilings",
}


def normalize_room(room: str | None) -> str:
    """Canonical room label: lowercase, spaces/hyphens folded, aliases mapped."""
    if not room:
        return ""
    key = room.strip().lower().replace(" ", "_").replace("-", "_")
    return _ROOM_ALIASES.get(key, key)


def pack_items_yaml(packs: list[Pack]) -> str:
    """Serialize pack items for the propose prompt, GROUPED by pack.

    Pass 2 Phase C: a multi-pack scan sends one propose request whose
    checklist is grouped by pack so the model keeps pack boundaries;
    the item_id values remain the contract.
    """
    grouped: dict[str, list[dict[str, object]]] = {}
    for pack in packs:
        grouped[pack.pack_id] = [
            {
                "item_id": item.id,
                "title": item.title,
                "kind": item.kind.value,
                "rooms": item.rooms,
                "severity": item.severity,
                "observable_evidence": item.observable_evidence,
                "sam_prompts": item.sam_prompts,
                "safety_prompts": item.safety_prompts,
            }
            for item in pack.items
        ]
    return yaml.safe_dump(grouped, sort_keys=False)


def dedupe_cannot_assess(entries: list[CannotAssess]) -> list[CannotAssess]:
    """Drop repeated (area, reason) entries, keeping the first."""
    seen: set[tuple[str, str]] = set()
    out: list[CannotAssess] = []
    for entry in entries:
        key = (entry.area.strip().lower(), entry.reason)
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def clean_cannot_assess(
    entries: list[CannotAssess],
    hazards: list[Hazard],
    rooms_seen: list[str],
) -> list[CannotAssess]:
    """Final couldn't-assess cleanup (smoke-test fix 3).

    Dedupes, drops entries naming an item that received a verdict
    (anything other than cannot_assess), and drops entries naming a
    room that was actually seen.
    """
    verdict_items = {h.item_id for h in hazards if h.verification is not Verification.CANNOT_ASSESS}
    seen_rooms = {normalize_room(r) for r in rooms_seen if normalize_room(r)}
    out: list[CannotAssess] = []
    for entry in dedupe_cannot_assess(entries):
        if entry.area.strip() in verdict_items:
            continue
        if normalize_room(entry.area) in seen_rooms:
            continue
        out.append(entry)
    return out


def _classify_missing_rooms(vision: VisionReasoner, keyframes: list[Keyframe]) -> None:
    """One classify_room call per still-unlabeled keyframe, in parallel.

    Providers with no opinion (mock/replay) return None and the frame
    simply stays unlabeled - the model's own room text is the fallback.
    """
    missing = [kf for kf in keyframes if not kf.room_guess and kf.image_path]
    if not missing or not hasattr(vision, "classify_room"):
        return

    def _one(kf: Keyframe) -> None:
        try:
            result = vision.classify_room(ImageRef(path=kf.image_path, keyframe_id=kf.id, t=kf.t))
        except Exception:
            return
        if isinstance(result, dict):
            room = normalize_room(str(result.get("room_type") or result.get("room") or ""))
            if room:
                kf.room_guess = room

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_one, missing))


def _sanitize_proposal(proposal: HazardProposal, batch: list[Keyframe]) -> None:
    """Snap model timestamps onto batch frames; stamp batch provenance.

    A timestamp counts only if it lands within tolerance of a keyframe
    in THIS proposal's batch. Anything else (missing, or numbers like
    0,1,2 that belong to some other batch) is treated as omitted: the
    proposal keeps no timestamps and the verifier searches the batch
    frames recorded in source_keyframe_ids instead.
    """
    if not batch:
        proposal.evidence_timestamps = []
        proposal.source_keyframe_ids = []
        return
    snapped: list[float] = []
    snapped_ids: list[str] = []
    for raw_t in proposal.evidence_timestamps:
        nearest = min(batch, key=lambda k: abs(k.t - float(raw_t)))
        if abs(nearest.t - float(raw_t)) <= _TIMESTAMP_TOLERANCE_S:
            if nearest.t not in snapped:
                snapped.append(nearest.t)
                snapped_ids.append(nearest.id)
    if snapped:
        proposal.evidence_timestamps = snapped
        proposal.source_keyframe_ids = snapped_ids
    else:
        proposal.evidence_timestamps = []
        proposal.source_keyframe_ids = [kf.id for kf in batch]
    # Room: the label of the frames the finding points at wins over the
    # model's free-text room. With batch-wide provenance (no usable
    # timestamps) only a unanimous batch room is safe to apply.
    by_id = {kf.id: kf for kf in batch}
    rooms: list[str] = []
    for kf_id in proposal.source_keyframe_ids:
        guess = by_id[kf_id].room_guess
        if guess:
            rooms.append(guess)
    if rooms and (snapped or len(set(rooms)) == 1):
        proposal.room = Counter(rooms).most_common(1)[0][0]
    elif proposal.room:
        proposal.room = normalize_room(proposal.room) or proposal.room


def propose_hazards(
    vision: VisionReasoner,
    packs: list[Pack],
    keyframes: list[Keyframe],
    narration_facts: list[NarrationFact],
    measurements: list[Measurement],
    batch_size: int = 12,
) -> tuple[list[HazardProposal], list[CannotAssess], list[str]]:
    """Run the propose pass. Returns (proposals, cannot_assess, rooms_seen)."""
    valid_ids = {item.id for pack in packs for item in pack.items}
    items_yaml = pack_items_yaml(packs)
    batches = [keyframes[i : i + batch_size] for i in range(0, max(len(keyframes), 1), batch_size)]
    if not keyframes:
        batches = [[]]

    def _run_batch(batch: list[Keyframe]) -> ProposeResponse:
        return vision.propose_hazards(
            ProposeRequest(
                pack_items_yaml=items_yaml,
                keyframes=batch,
                narration_facts=[f.fact for f in narration_facts],
                measurements=[f"{m.label}: {m.value} {m.unit}" for m in measurements],
                previous_findings_summary="",
            )
        )

    if len(batches) > 1:
        with ThreadPoolExecutor(max_workers=min(8, len(batches))) as pool:
            responses = list(pool.map(_run_batch, batches))
    else:
        responses = [_run_batch(batches[0])]

    # One room label per keyframe, from the per-image labels first.
    for batch, response in zip(batches, responses, strict=True):
        labels = getattr(response, "keyframe_rooms", []) or []
        # Labels are aligned by image order; a short list labels a prefix.
        for kf, label in zip(batch, labels):
            room = normalize_room(label)
            if room and not kf.room_guess:
                kf.room_guess = room
    _classify_missing_rooms(vision, keyframes)

    found: dict[tuple[str, str], HazardProposal] = {}
    cannot: list[CannotAssess] = []
    model_rooms: list[str] = []
    for batch, response in zip(batches, responses, strict=True):
        for proposal in response.proposals:
            if proposal.item_id not in valid_ids:
                continue  # the model may only use pack item_ids (spec 9.4.5)
            _sanitize_proposal(proposal, batch)
            found.setdefault((proposal.item_id, proposal.room), proposal)
        cannot.extend(response.cannot_assess)
        for room in response.rooms_seen:
            normalized = normalize_room(room)
            if normalized and normalized not in model_rooms:
                model_rooms.append(normalized)
    # rooms_seen is the keyframe labels when we have them - one source
    # of truth - and the model's aggregate list only as a fallback.
    rooms_seen: list[str] = []
    for kf in keyframes:
        if kf.room_guess and kf.room_guess not in rooms_seen:
            rooms_seen.append(kf.room_guess)
    if not rooms_seen:
        rooms_seen = model_rooms
    return list(found.values()), dedupe_cannot_assess(cannot), rooms_seen
