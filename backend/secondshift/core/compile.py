"""compile_checklist: pack ids or plain-English lines -> a Checklist.

A Checklist wraps a Pack (the pipeline's native checklist format)
plus its provenance. Plain-English lines are compiled one by one by
the vision provider (Spark live; a deterministic stub in mock mode);
a line the compiler refuses stays a refusal with its reason - it
never becomes a fake item. Custom checklists are drafts, labelled
"Custom checklist - not reviewed by an expert", and excluded from
eval by their draft status.
"""

import hashlib
from dataclasses import dataclass, field

from secondshift.checklists.loader import Pack, PackFix, PackItem, load_all_packs
from secondshift.domain.enums import ItemKind
from secondshift.providers.base import VisionReasoner

CUSTOM_LABEL = "Custom checklist - not reviewed by an expert"


@dataclass
class Checklist:
    """A validated checklist: a Pack plus compile provenance."""

    pack: Pack
    source: str  # "packs" | "custom"
    refusals: list[dict[str, str]] = field(default_factory=list)

    @property
    def label(self) -> str:
        return CUSTOM_LABEL if self.source == "custom" else self.pack.title


def _str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _item_from_compiled(line: str, data: dict[str, object], idx: int) -> PackItem | None:
    """Validate one compiled dict into a PackItem; None if malformed."""
    try:
        kind = ItemKind(str(data.get("kind", "presence")))
        if kind not in (ItemKind.PRESENCE, ItemKind.ABSENCE):
            kind = ItemKind.PRESENCE
        raw_severity = data.get("severity", 2)
        severity = raw_severity if isinstance(raw_severity, int) else 2
        if severity not in (1, 2, 3):
            severity = 2
        sam_prompts = _str_list(data.get("sam_prompts"))
        if kind is ItemKind.PRESENCE and not sam_prompts:
            return None
        rooms = _str_list(data.get("rooms")) or ["any"]
        return PackItem(
            id=f"CUSTOM-{idx:02d}",
            title=str(data.get("title") or line).strip(),
            kind=kind,
            rooms=rooms,
            severity=severity,
            observable_evidence=str(data.get("observable_evidence") or line),
            sam_prompts=sam_prompts,
            safety_prompts=_str_list(data.get("safety_prompts")),
            thin_object=bool(data.get("thin_object", False)),
            fixes=[
                PackFix(
                    id=f"custom-{idx:02d}-fix",
                    title="Fix it",
                    how="Follow the finding's description and make the area safe.",
                    difficulty="easy",
                    cost_estimate="varies",
                    visualization_prompt=None,
                )
            ],
            sources=[],
        )
    except Exception:
        return None


def compile_checklist(
    source: list[str], vision: VisionReasoner | None = None
) -> Checklist:
    """Compile pack ids and/or plain-English lines into a Checklist.

    Entries that match a known pack id load that pack (several packs
    merge into one checklist). Every other entry is treated as a
    plain-English line for the compiler. Lines the compiler refuses -
    or that fail validation - land in Checklist.refusals with their
    reason; they never silently become items.
    """
    packs_by_id = load_all_packs()
    pack_ids = [s for s in source if s in packs_by_id]
    lines = [s for s in source if s not in packs_by_id]
    if pack_ids and not lines:
        packs = [packs_by_id[pid] for pid in pack_ids]
        if len(packs) == 1:
            return Checklist(pack=packs[0], source="packs")
        merged = Pack(
            pack_id="merged-" + "-".join(pack_ids),
            title=" + ".join(p.title for p in packs),
            audience="; ".join(p.audience for p in packs),
            high_risk_zones=sorted({z for p in packs for z in p.high_risk_zones}),
            severity_weights={1: 1.0, 2: 2.0, 3: 3.0},
            items=[item for p in packs for item in p.items],
        )
        return Checklist(pack=merged, source="packs")
    items: list[PackItem] = []
    refusals: list[dict[str, str]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        compiled = vision.compile_checklist_item(line) if vision is not None else None
        if compiled is None:
            refusals.append(
                {"line": line, "reason": "No checklist compiler is available."}
            )
            continue
        if compiled.get("status") == "refused":
            refusals.append(
                {"line": line, "reason": str(compiled.get("reason") or "Refused.")}
            )
            continue
        item = _item_from_compiled(line, compiled, len(items) + 1)
        if item is None:
            refusals.append(
                {"line": line, "reason": "The compiler's answer was not usable."}
            )
            continue
        items.append(item)
    digest = hashlib.sha256("\n".join(lines).encode()).hexdigest()[:8]
    pack = Pack(
        pack_id=f"custom-{digest}",
        title="Custom checklist",
        audience=CUSTOM_LABEL,
        status="draft",
        high_risk_zones=[],
        severity_weights={1: 1.0, 2: 2.0, 3: 3.0},
        items=items,
    )
    return Checklist(pack=pack, source="custom", refusals=refusals)
