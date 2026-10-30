"""Resolve a pack id to a Pack: built-in packs first, then custom
checklists stored by the bring-your-own-checklist flow (Pass 3 P4).
"""

from secondshift.checklists.loader import Pack, load_all_packs
from secondshift.storage.repository import Repository


def resolve_pack(store: Repository, pack_id: str) -> Pack | None:
    packs = load_all_packs()
    if pack_id in packs:
        return packs[pack_id]
    raw = store.get("custom_pack", pack_id)
    if raw is None:
        return None
    try:
        return Pack.model_validate(raw)
    except Exception:
        return None


def resolve_packs(store: Repository, pack_ids: list[str]) -> list[Pack]:
    resolved: list[Pack] = []
    for pack_id in pack_ids:
        pack = resolve_pack(store, pack_id)
        if pack is not None:
            resolved.append(pack)
    return resolved
