"""Fix plan (spec section 9.8).

The planner may ONLY choose from the pack's fix library - it never invents
products, brands or prices. On mocks the choice is deterministic (the
library order is the pack author's ranking); the real path uses
prompts/fix_plan.md with Spark to pick + phrase steps, validated against
the same library.
Depends on: checklists.loader, domain.hazards.
"""

from secondshift.checklists.loader import Pack, PackFix
from secondshift.domain.enums import Verification
from secondshift.domain.hazards import FixCard, FixOption, Hazard


def _to_option(fix: PackFix) -> FixOption:
    return FixOption.model_validate(fix, from_attributes=True)


def build_fix_cards(hazards: list[Hazard], packs: list[Pack]) -> list[FixCard]:
    """Build one FixCard per ranked (confirmed / needs-human) hazard."""
    items = {item.id: item for pack in packs for item in pack.items}
    cards: list[FixCard] = []
    for hazard in hazards:
        if hazard.verification not in (Verification.CONFIRMED, Verification.NEEDS_HUMAN):
            continue
        item = items.get(hazard.item_id)
        if item is None or not item.fixes:
            continue
        chosen = _to_option(item.fixes[0])
        alternatives = [_to_option(f) for f in item.fixes[1:]]
        steps = [chosen.how, "Take a photo of the finished fix so the re-check can see it."]
        cards.append(
            FixCard(
                id=f"fix-{hazard.id}",
                hazard_id=hazard.id,
                chosen=chosen,
                alternatives=alternatives,
                plain_language_steps=steps[:5],
            )
        )
    return cards
