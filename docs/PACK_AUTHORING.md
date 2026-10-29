# Writing a checklist pack (under 30 minutes)

A pack is one YAML file in `backend/secondshift/checklists/packs/`.
Adding a use case = adding a file. No code changes.

## Start

```
make new-pack NAME=garage_safety
```

This scaffolds a valid **draft** pack. Drafts can be scanned with, and
their reports carry a "Draft checklist — not reviewed by an expert"
banner (Phase C.6 UI rule) and are excluded from eval.

## The schema

Pack level: `version`, `status` (`draft` until a human expert reviews
it, then `approved`), `pack_id` (snake_case), `title`, `audience`
(one line: who it's for), `high_risk_zones` (room names), and
`severity_weights` (copy the standard 1/2/3 weights).

Each item:

- `id` — UPPER-KEBAB with the pack prefix (`GARAGE-...`). Unique.
- `title` — one plain sentence a worried family member understands.
- `kind` — `presence` (a dangerous thing is there), `absence` (a
  safety thing is missing), `measurement` (a number the family
  enters), or `interaction` (decided by the routine clip).
- `rooms` — where it applies (`any` is allowed).
- `severity` — 1, 2 or 3. 3 = could seriously hurt someone soon.
- `observable_evidence` — what the camera must actually SEE. If a
  camera cannot see it, the item does not belong in the pack.
- `sam_prompts` — 1–3 short noun phrases (≤ 5 words) naming the
  OBJECT: `throw rug`, not `a dangerous rug on the floor`.
- `safety_prompts` — absence items only: noun phrases for the missing
  safety object (`grab bar`). Verification runs SAM for the anchor
  (in `sam_prompts`) and the safety object on the same frames.
- `cannot_see_note` — when the honest answer is often "can't tell",
  say why in one line (`We cannot see inside drawers`).
- `measurement_threshold` — measurement items only, and ONLY with a
  source. No source, no threshold.
- `dedupe_key` — optional. Items in different packs that describe
  the same physical object share a key (`rug_on_path`) so a
  multi-pack scan reports it once, tagged with both packs.
- `fixes` — the library. Fixes are chosen ONLY from this list.
  The first fix should be the best default. Each fix: `id`, `title`,
  `how` (≤ 5 plain steps, one string), `difficulty`
  (easy/medium/pro), `cost_estimate` (always an estimate).
- `visualization_prompt` — on the top fix when the fix is visual
  (install / add / remove / move / anchor / cover). Write it as a
  masked-edit instruction: "Add a stainless-steel grab bar mounted
  on the wall to the right of the toilet". When the fix is not
  visual, set it to `null` and add a YAML comment saying why.
- `sources` — REQUIRED for approved packs (the loader refuses
  otherwise). Name the guidance the item paraphrases. If the team
  still has to verify it, write `'TODO(SOURCE): ...'` — never invent
  a citation, a statistic, or a threshold.

## Rules that keep packs honest

1. Paraphrase guidance; never copy text.
2. No medical claims. The pack screens spaces; it never diagnoses.
3. Every claim a family would act on traces to `sources`.
4. Impact facts live in `docs/IMPACT.md` per pack — sourced, or
   `TODO(STAT)`. Never invent a statistic.

## Test it

```
.venv/bin/python -c "from secondshift.checklists.loader import load_pack; load_pack('backend/secondshift/checklists/packs/<name>.yaml')"
make check
```
