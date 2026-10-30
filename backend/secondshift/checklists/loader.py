"""Checklist pack loader and validation.

Why: packs are the generality mechanism - adding a use case means adding
one YAML file, no code change. This loader is the only place pack YAML is
parsed, and it validates structure so a bad pack fails at startup, loudly.
Depends on: pydantic, yaml, domain.enums (ItemKind, Severity).
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from secondshift.domain.enums import ItemKind

PACKS_DIR = Path(__file__).parent / "packs"


class PackFix(BaseModel):
    """One fix in a pack item's library (mirrors domain FixOption)."""

    id: str
    title: str
    how: str
    difficulty: Literal["easy", "medium", "pro"]
    cost_estimate: str
    visualization_prompt: str | None = None


class PackItem(BaseModel):
    """One checklist item in a pack (Appendix A schema)."""

    id: str
    title: str
    kind: ItemKind
    rooms: list[str]
    severity: int
    observable_evidence: str
    sam_prompts: list[str]
    safety_prompts: list[str] = Field(default_factory=list)
    cannot_see_note: str | None = None
    fixes: list[PackFix]
    sources: list[str] = Field(default_factory=list)
    measurement_threshold: str | None = None
    dedupe_key: str | None = None
    needs_human_unless: str | None = None
    # Pass 3 P1: thin/elongated objects (cords, towels, straps) are
    # swept on tiled crops instead of wide frames.
    thin_object: bool = False
    # Pass 3 P1: when set, the sweep segments these anchor prompts too
    # and only confirms the item when a found object overlaps (or sits
    # within 10% of frame width of) an anchor box on the same frame.
    sweep_anchor_prompts: list[str] = Field(default_factory=list)

    @field_validator("severity")
    @classmethod
    def _severity_range(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError("severity must be 1, 2 or 3")
        return v

    @field_validator("id")
    @classmethod
    def _id_shape(cls, v: str) -> str:
        if not v or v.upper() != v or " " in v:
            raise ValueError("item id must be UPPER-KEBAB, e.g. FALL-FLOOR-RUG")
        return v


class Pack(BaseModel):
    """A checklist pack: one use case, as data."""

    version: int = 1
    status: Literal["approved", "draft"] = "approved"
    demo: bool = True
    pack_id: str
    title: str
    audience: str
    high_risk_zones: list[str]
    severity_weights: dict[int, float]
    items: list[PackItem]

    @field_validator("items")
    @classmethod
    def _unique_item_ids(cls, v: list[PackItem]) -> list[PackItem]:
        ids = [i.id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate item ids in pack")
        if not v:
            raise ValueError("a pack must contain at least one item")
        return v


def _enforce_sources(pack: "Pack", path: str | Path) -> None:
    """An approved pack may not ship items without sources (pass 2 C.1).

    Draft packs are exempt - they are visibly unreviewed in the product.
    A TODO(SOURCE) entry counts: it names what the team must verify.
    """
    if pack.status != "approved":
        return
    missing = [item.id for item in pack.items if not item.sources]
    if missing:
        raise ValueError(
            f"Approved pack {pack.pack_id} ({path}) has items without sources: {', '.join(missing)}"
        )


def load_pack(path: str | Path) -> Pack:
    """Load and validate one pack YAML file.

    Example: ``load_pack(PACKS_DIR / "falls_older_adults.yaml").pack_id``
    returns ``"falls_older_adults"``.
    """
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"Pack file {path} did not parse to a mapping.")
    pack = Pack.model_validate(raw)
    _enforce_sources(pack, path)
    return pack


def load_all_packs(packs_dir: str | Path = PACKS_DIR) -> dict[str, Pack]:
    """Load every pack in the packs directory, keyed by pack_id."""
    packs: dict[str, Pack] = {}
    for path in sorted(Path(packs_dir).glob("*.yaml")):
        pack = load_pack(path)
        if pack.pack_id in packs:
            raise ValueError(f"duplicate pack_id {pack.pack_id}")
        packs[pack.pack_id] = pack
    return packs
