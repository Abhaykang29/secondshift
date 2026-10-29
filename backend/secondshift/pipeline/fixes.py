"""Fix plan (spec section 9.8).

The planner may ONLY choose from the pack's fix library - it never invents
products, brands or prices. On mocks the choice is deterministic (the
library order is the pack author's ranking); the real path uses
prompts/fix_plan.md with Spark to pick + phrase steps, validated against
the same library.
Depends on: checklists.loader, domain.hazards.
"""

import logging

from secondshift.checklists.loader import Pack, PackFix
from secondshift.domain.enums import Verification
from secondshift.domain.hazards import FixCard, FixOption, Hazard


def _to_option(fix: PackFix) -> FixOption:
    return FixOption.model_validate(fix, from_attributes=True)


def build_fix_cards(
    hazards: list[Hazard],
    packs: list[Pack],
    vision: object | None = None,
    language: str = "en",
) -> list[FixCard]:
    """Build one FixCard per ranked (confirmed / needs-human) hazard.

    Pass 2 E.6: when a live vision provider is present, Spark picks the
    fix via prompts/fix_plan.md - from the library ONLY. Any choice
    outside the library (or unusable steps) falls back to the library
    order, logged. The mock provider returns None -> deterministic.
    """
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
        if vision is not None:
            choice = vision.plan_fix(  # type: ignore[attr-defined]
                hazard.title,
                hazard.description,
                [
                    {"id": f.id, "title": f.title, "how": f.how,
                     "difficulty": f.difficulty, "cost_estimate": f.cost_estimate}
                    for f in item.fixes
                ],
                language,
            )
            if choice:
                by_id = {f.id: f for f in item.fixes}
                picked = by_id.get(str(choice.get("chosen_fix_id", "")))
                raw_steps = choice.get("plain_language_steps") or []
                clean_steps = [str(s) for s in raw_steps if str(s).strip()][:5]
                if picked is not None and clean_steps:
                    chosen = _to_option(picked)
                    alternatives = [
                        _to_option(f) for f in item.fixes if f.id != picked.id
                    ]
                    steps = clean_steps
                else:
                    logging.getLogger(__name__).info(
                        "fix_plan choice rejected for %s (not in library or no steps); "
                        "fell back to library order",
                        hazard.item_id,
                    )
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
