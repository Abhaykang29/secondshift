"""Scaffold a new checklist pack (pass 2 Phase C).

Usage: .venv/bin/python scripts/new_pack.py NAME=my_pack_id
Writes a valid DRAFT pack YAML with one example item; the loader
accepts it immediately (drafts are exempt from the sources rule, and
the scaffold carries a TODO(SOURCE) anyway).
"""
import sys
from pathlib import Path

PACKS = Path(__file__).parent.parent / "backend" / "secondshift" / "checklists" / "packs"

TEMPLATE = """version: 1
status: draft
pack_id: {name}
title: TODO - name this use case
audience: TODO - who is this for
high_risk_zones:
- living
severity_weights:
  1: 1.0
  2: 2.0
  3: 3.0
items:
- id: {prefix}-EXAMPLE-ITEM
  title: TODO - one plain sentence naming the hazard
  kind: presence
  rooms:
  - any
  severity: 2
  observable_evidence: TODO - what the camera must actually see
  sam_prompts:
  - short noun phrase
  safety_prompts: []
  cannot_see_note: null
  fixes:
  - id: {slug}-example-fix
    title: TODO - the fix, in plain words
    how: TODO - one or two plain steps.
    difficulty: easy
    cost_estimate: free
    visualization_prompt: null
    # explain here if this fix is not visual
  sources:
  - 'TODO(SOURCE): name the guidance this item is based on'
"""


def main() -> int:
    args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    name = args.get("NAME", "")
    if not name or not name.replace("_", "").isalnum() or name != name.lower():
        print("Usage: new_pack.py NAME=snake_case_id")
        return 2
    target = PACKS / f"{name}.yaml"
    if target.exists():
        print(f"{target} already exists")
        return 2
    prefix = name.split("_")[0].upper()[:5]
    target.write_text(
        TEMPLATE.format(name=name, prefix=prefix, slug=name.replace("_", "-"))
    )
    print(f"Wrote draft pack {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
