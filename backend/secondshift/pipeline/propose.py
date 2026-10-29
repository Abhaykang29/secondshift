"""Propose hazards (spec section 9.4).

Builds the pack-items request, calls the VisionReasoner in batches of
PROPOSE_BATCH keyframes in order, drops unknown item_ids, and dedupes
across batches. Output must validate as HazardProposal (the provider
contract guarantees it).
Depends on: providers.base, checklists.loader, domain models.
"""

import yaml

from secondshift.checklists.loader import Pack
from secondshift.domain.checkup import Keyframe, Measurement, NarrationFact
from secondshift.domain.hazards import CannotAssess, HazardProposal
from secondshift.providers.base import ProposeRequest, VisionReasoner


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
    found: dict[tuple[str, str], HazardProposal] = {}
    cannot: list[CannotAssess] = []
    rooms_seen: list[str] = []
    summary = ""
    batches = [keyframes[i : i + batch_size] for i in range(0, max(len(keyframes), 1), batch_size)]
    if not keyframes:
        batches = [[]]
    for batch in batches:
        response = vision.propose_hazards(
            ProposeRequest(
                pack_items_yaml=items_yaml,
                keyframes=batch,
                narration_facts=[f.fact for f in narration_facts],
                measurements=[f"{m.label}: {m.value} {m.unit}" for m in measurements],
                previous_findings_summary=summary,
            )
        )
        for proposal in response.proposals:
            if proposal.item_id not in valid_ids:
                continue  # the model may only use pack item_ids (spec 9.4.5)
            found.setdefault((proposal.item_id, proposal.room), proposal)
        cannot.extend(response.cannot_assess)
        for room in response.rooms_seen:
            if room not in rooms_seen:
                rooms_seen.append(room)
        summary = "; ".join(f"{p.item_id} in {p.room}" for p in found.values())
    return list(found.values()), cannot, rooms_seen
