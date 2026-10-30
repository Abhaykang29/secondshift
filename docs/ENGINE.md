# The SecondShift engine layer

SecondShift the app is one client of a reusable engine: give the
engine a checklist in plain English and a video, and it returns
evidence-backed verdicts - yes / no / can't tell - plus a re-check
that confirms whether a fix actually happened.

## The pipeline

```
Checklist (plain English)
  -> Capture (phone, glasses, fixed camera)
  -> Propose (Muse Spark) + Sweep (SAM 3.1)
  -> Verify (SAM 3.1 + Muse Spark judge)
  -> Verdict (yes / no / can't tell + evidence frames and boxes)
  -> Fix & Re-check (diff against the last check)
```

- **Propose** reads batches of keyframes and names candidate hazards
  from the checklist, one room label per frame.
- **Sweep** runs the other direction: SAM segments each checklist
  item's own prompts (tiled crops for thin objects) and the judge
  confirms or rejects the hits. Two directions, because each catches
  what the other misses.
- **Verify** never lets a language model grade its own homework:
  presence needs a SAM box, absence needs the anchor visible and the
  safety object missing, and items a camera cannot settle (tightness,
  hidden anchors) stop at "needs a human look" or "can't tell" by
  design.
- People are blurred in every frame before any of this reads them.

## Python interface (`secondshift.core`)

```python
core.compile_checklist(text_or_pack_ids, vision) -> Checklist
core.check(video, checklist, providers, settings, work_dir) -> CheckResult   # a Report
core.recheck(previous, video, checklist, providers, settings, work_dir) -> RecheckResult
core.compile_rule(sentence, vision) -> RuleSpec | Refusal   # a RuleSpec with a refused status
core.live(spec, source_id, providers, work_dir, on_event) -> LiveWatch
```

Nothing in `core/` imports the app layer (`secondshift.api`) or any
UI code; packs and custom checklists enter only as data. A test
(`tests/test_core_boundary.py`) enforces the boundary.

## REST API (`/v1`)

Mounted at `/v1` with its own OpenAPI document at `/v1/openapi.json`
(interactive docs at `/v1/docs`).

| Endpoint | What it does |
|---|---|
| `POST /v1/checklists` | `{pack_ids}` and/or `{lines}` → a validated checklist (compiled items + per-line refusals). Custom checklists are stored and labelled "Custom checklist — not reviewed by an expert". |
| `POST /v1/checks` | multipart: `video` file + `checklist_id` → `{job_id}`; the check runs in the background. |
| `GET /v1/checks/{job_id}` | status, and on completion the full result JSON: verdicts, evidence boxes and frames, cannot-assess list, fixes. |
| `POST /v1/checks/{job_id}/recheck` | multipart: new `video` → a re-check job diffing against the original check. |
| `POST /v1/rules/compile` | `{sentence}` → a compiled live-check rule, or an honest refusal with alternatives. |

**Auth:** `X-API-Key` header. Keys are configured with the
`V1_API_KEYS` environment variable as `name:key,name:key`. When it
is unset, a single local development key `local-dev-key` is accepted
- local use only; set real keys before exposing the API anywhere.

**Limits:** 30 requests per minute per key (429 past that). All
model spend flows through the same transport cost guard and budget
(`BUDGET_USD`) as the app, and every call lands in the same SQLite
cost ledger.

## Bring your own checklist

In the app: the "Custom check" card on the Check tab. Type 3–10
lines ("trailer doors closed and sealed", "fire extinguisher mounted
by the exit", "no boxes stacked above shoulder height"). Each line is
compiled into an item (kind, SAM prompts, safety prompts, thin-object
flag) or refused with a reason ("can't verify tightness from video").
You confirm the compiled items, then the scan runs like any pack.
Custom checklists are drafts: labelled, and excluded from eval.

## Where the same layer goes next (roadmap only - none of this is built)

1. **Robots:** an independent check that a chore was actually done
   and nothing was left on the walking path.
2. **Workplaces:** daily safety walks against the site's own rules.
3. **Trucking:** walk-around and cargo-securement checks against
   written rules.
4. **Rentals and returns:** before/after condition proof from two
   walkthrough videos.
5. **Disaster response:** coarse damage triage from residents' videos.
