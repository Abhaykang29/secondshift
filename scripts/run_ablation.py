"""Pass 3 P6 ablations on the one labeled real video (test_1.mp4).

Ground truth (the user, 2026-10-30): 8 findings in his own walkthrough.
Scoring follows the P1 acceptance convention:
- T1 floor cord: FALL-FLOOR-CORD under its own id (strict). The
  family variant counts the same cords reported as PET-CORDS-CHEWABLE
  with cross-pack tags.
- T2 TV cords: a cord item (FALL-FLOOR-CORD or PET-CORDS-CHEWABLE)
  reported in the living room.
- T3 desk cords: a cord item in the bedroom (the desk's room).
- T4 plant in the cat's reach: PET-TOXIC-PLANT.
- T5 towels on the oven handle: FIRE-STOVE-COMBUSTIBLES, kitchen.
- T6 pet bowls by the balcony door: PET-TOXIC-FOOD-LOW (the pet
  pack's food-in-bowls item).
- T7 no bedside lamp: FALL-BED-LIGHT-REACH.
- T8 extinguisher not visible: FIRE-EXTINGUISHER-ABSENT as
  needs_human (the honest verdict for a hidden safety item).
Precision: reported (confirmed + needs_human) hazards in the six
ground-truth families / all reported hazards.

Configs: full (sweep + thin tiles), no-sweep, no-thin.
Runs in-process on the acceptance capture's stored keyframes (files
already person-blurred), live providers in record mode - identical
calls hit the recorded cache, changed calls go live and are costed
in the ledger under the phase tag.

Usage: python scripts/run_ablation.py
"""

import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
os.environ.setdefault("PROVIDER", "meta")
os.environ.setdefault("CACHE_MODE", "record")
os.environ.setdefault("SECONDSHIFT_PHASE_TAG", "pass3-ablation")

from secondshift.checklists.loader import load_all_packs  # noqa: E402
from secondshift.config import Settings  # noqa: E402
from secondshift.domain.checkup import Checkup, Consent, Keyframe  # noqa: E402
from secondshift.pipeline.scan import ScanInput, run_scan  # noqa: E402
from secondshift.providers.registry import build_providers  # noqa: E402
from secondshift.storage.repository import Repository  # noqa: E402

CAPTURE_ID = "5962c3ab6c604630abfa8da9839d1551"  # the P1 acceptance capture
CORDS = {"FALL-FLOOR-CORD", "PET-CORDS-CHEWABLE"}
FAMILIES = CORDS | {
    "PET-TOXIC-PLANT",
    "FIRE-STOVE-COMBUSTIBLES",
    "PET-TOXIC-FOOD-LOW",
    "FALL-BED-LIGHT-REACH",
    "FIRE-EXTINGUISHER-ABSENT",
}


def score(hazards: list) -> dict:  # type: ignore[type-arg]
    rep = [h for h in hazards if h.verification.value in ("confirmed", "needs_human")]

    def has(item_ids: set, room: str | None = None) -> bool:
        return any(
            h.item_id in item_ids and (room is None or h.room == room) for h in rep
        )

    targets = {
        "T1 floor cord (own id)": has({"FALL-FLOOR-CORD"}),
        "T2 TV cords (living)": has(CORDS, "living"),
        "T3 desk cords (bedroom)": has(CORDS, "bedroom"),
        "T4 plant": has({"PET-TOXIC-PLANT"}),
        "T5 towels (kitchen)": has({"FIRE-STOVE-COMBUSTIBLES"}, "kitchen"),
        "T6 pet bowls": has({"PET-TOXIC-FOOD-LOW"}),
        "T7 bed lamp": has({"FALL-BED-LIGHT-REACH"}),
        "T8 extinguisher NH": any(
            h.item_id == "FIRE-EXTINGUISHER-ABSENT"
            and h.verification.value == "needs_human"
            for h in rep
        ),
    }
    strict = sum(targets.values())
    family = strict + (0 if targets["T1 floor cord (own id)"] else (1 if targets["T2 TV cords (living)"] else 0))
    in_family = sum(1 for h in rep if h.item_id in FAMILIES)
    return {
        "targets": targets,
        "recall_strict": f"{strict}/8",
        "recall_family": f"{family}/8",
        "precision": f"{in_family}/{len(rep)}" if rep else "0/0",
        "reported": len(rep),
    }


def main() -> int:
    settings = Settings.load()
    providers = build_providers(settings)
    store = Repository("data/store.json")
    raw = store.get("keyframes", CAPTURE_ID)
    assert raw, "acceptance capture keyframes missing"
    keyframes = [Keyframe.model_validate(k) for k in raw["keyframes"]]
    packs = [
        load_all_packs()[p]
        for p in ("falls_older_adults", "fire_safety", "pet_safety")
    ]
    configs = [
        ("full (sweep + thin tiles)", {"sweep": True}),
        ("no-sweep", {"sweep": False}),
        ("no-thin (sweep, thin tiles off)", {"sweep": True, "thin_sweep_budget": 0}),
    ]
    for name, kwargs in configs:
        checkup = Checkup(
            id=f"ablation-{abs(hash(name)) % 10**8}",
            created_at=datetime.now(UTC),
            pack_ids=[p.pack_id for p in packs],
            consent=Consent(resident_informed=True, no_private_moments=True),
        )
        t0 = time.time()
        out = run_scan(
            providers,
            ScanInput(checkup=checkup, packs=packs, keyframes=keyframes, **kwargs),
        )
        elapsed = time.time() - t0
        result = score(out.hazards)
        print(f"\n== {name}  ({elapsed:.0f}s, CA {len(out.cannot_assess)})")
        for target, hit in result["targets"].items():
            print(f"   {'HIT ' if hit else 'miss'} {target}")
        print(
            f"   recall strict {result['recall_strict']} | family {result['recall_family']}"
            f" | precision {result['precision']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
