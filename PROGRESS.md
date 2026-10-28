# Progress

## Phase 0 - Contracts and skeleton (Oct 28) - APPROVED by user 2026-10-28

## Fixes before Phase 1 (2026-10-28) - DONE
- types.ts is now GENERATED from Pydantic JSON schemas (`make types`); drift test is field-level/exact-diff.
- eslint (flat config, typescript-eslint) wired into `make check`.
- Mock scenarios expanded: parent_home_demo = 10 proposals (9 real hazards incl. 3 absence + 1 interaction, plus 1 labelled SAM-rejected false positive for the ablation), baby_home_demo = 7 hazards, plus parent_home_fixed for re-check.

## Phase 1 - Capture (Oct 28) - DONE
- ffprobe probe with friendly >6min rejection; ffmpeg frame extraction at SAMPLE_FPS; audio extraction; quality metrics (Laplacian variance + mean luma); keyframe selection (descriptor change + max-gap, cap 80).
- Synthetic video generator is real: 60s, 6 labelled scenes, walking PERSON blob, hallway dresser-touch moment.
- Verified end to end via API: create checkup (consent enforced, 422 without it) -> upload synthetic -> 58 keyframes.
- Acceptance: synthetic video produces 58 keyframes (spec range 40-80) with default thresholds.
- [x] Repo layout per spec 7.3, Makefile, .env.example, docs stubs
- [x] Domain schemas (spec section 8) with docstrings; enums; config
- [x] Provider interfaces, registry, mock skeleton, record/replay cache, cost guard (+ tests)
- [x] Pack loader + validation; full falls (16 items) and babyproofing (13 items) packs; fire safety pack (6 items, stretch - written early as data only)
- [x] FastAPI app: health + packs + costs live; all other resources stubbed with 501
- [x] Frontend shell: all routes as placeholder pages; typed API client; i18n en/hi
- [x] Prompt templates (all 10 required) with version headers
- [x] Eval skeleton: ablation configs, Appendix B sentences, metrics stub

### Verified (2026-10-28)
`make check` exit 0: ruff clean, ruff format clean, `mypy --strict` clean (51 files), **27 pytest passed**, `tsc --noEmit` clean. `make dev` verified live: backend `/api/health` ok, `/api/packs` returns falls=16 items / babyproofing=13, frontend serves 200 on :5173 and proxies /api. `make smoke-meta` correctly reports no META_API_KEY. Cost estimator sanity: ~$0.19/scan rough estimate at default settings.

### What's mocked
Everything model-facing: mock vision returns no proposals (Phase 2 wires scenarios), mock SAM returns deterministic masks, mock image editor returns a placeholder PNG, mock transcriber returns no segments. Meta adapters raise ProviderUnavailable.

### What's risky
- TODO(API): every Meta endpoint detail is unverified until keys arrive (Phase 7, smoke test first).
- TODO(STAT): babyproofing statistics placeholder - team must source from CPSC/AAP.
- TODO(TEAM): no real footage, labels or consent artefacts yet; eval datasets are empty manifests.
- Frontend eslint is not yet in `make check` (tsc is); add eslint config before Phase 3 UI work grows.

## Phase 2 - Scan pipeline on mocks (Oct 28) - DONE
- Mock providers are now scenario-driven and mutually consistent: vision proposes the scenario, SAM returns nothing for scenario-absent objects, transcriber speaks scenario narration.
- Pipeline: propose (batched, pack-ids only) -> verify (presence/absence/measurement/interaction per section 9.5, verify modes none/sam/sam_plus_judge) -> routine (pure geometry: support contacts, path obstacles) -> dedupe -> rank (exact section 9.7 formula).
- Job runner persists steps; re-runs skip completed steps. Scan API: POST /checkups/{id}/scan, GET report + job status.
- Acceptance snapshot (locked in tests): parent scenario = 9 confirmed + 1 rejected (the planted pet-bowl false positive SAM kills), rug #1 (risk 5.7, on routine path), 2 routine insights, deterministic across runs. Baby scenario = 7/7 confirmed.

## Phase 3 - Fixes, visualizations, report UI, sharing (Oct 28) - DONE
- Fix planner chooses ONLY from pack libraries (test asserts every chosen id exists in a pack); steps <= 5.
- Visualizations: top 3 viz-prompt hazards get before/after PNGs, watermark burned in ("Visualization - not a photo"), served via /api/reports/{id}/image/{name}.
- Reports: JSON + printable Jinja HTML + WhatsApp share text/wa.me link; fix tracker PATCH persists into the report.
- Frontend: real CheckupNew (consent enforced), Processing (job polling), ReportPage (fix-first-5, SAM overlay cards with SVG masks, absence "missing here" treatment, routine insights, fix plan, before/after slider, needs-human + couldn't-check, share/print), Fixes tracker with progress bar.
- Screenshots at phone width (390px) in docs/screenshots/: home, report (full page), fixes - captured with Playwright headless shell via scripts/screenshot_report.py. Report screenshot visually verified.
- Found + fixed during Phase 3: scan router registration had been silently dropped by an unused-import cleanup in Phase 2 - the Phase 3 API tests caught it; routes now covered by HTTP tests.

## Phase 4 - Re-check + rules (Oct 28) - DONE
- Observability precheck (8 flag families) + deterministic mock compiler + validator. Appendix B locked in tests: precheck >=95% (actual 100% of refused/compiled expectations), compiler statuses 40/40, primitives 40/40, every refusal offers alternatives.
- Check-up rule evaluation (SAM + state judge; watch-only primitives report "Needs Watch mode").
- Re-check diff: Resolved/Still/New/CannotTell with documented score (100 - min(100, 2 x open risk)). API test: rug + grab bar resolved, cord still present, bed-light NEW, score rises, saved night-light rule evaluates MET on the fixed home.
- Frontend: real RulesPage (example chips, compiled/refusal/clarification cards, JSON toggle, tappable alternatives) and RecheckPage (diff list, score before to after, rule outcomes).

## Phase 5 - Eval harness (Oct 28) - DONE (acceptance gate for Phase 6 passed)
- Metrics (item+room matching per Appendix D; mask_iou unit-tested for the labelling flow), synthetic manifest from the two scenarios, 4 ablation configs, matplotlib charts, summary.md + results.json per run.
- The ablation tells the designed story on mocks: spark_only precision 0.9412 (the planted pet-bowl false positive) -> spark_sam / wonder_sam precision 1.0, recall 1.0. Compiler metrics in the same report: status + primitive accuracy 1.0 on Appendix B.
- Every report carries the honest caveat: mock numbers validate the harness, NOT product accuracy; human-labelled captures remain TODO(TEAM) (see open TODO list).
- /eval page renders the latest run (GET /api/eval/latest); labelling UI page exists; the human labelling itself is TODO(TEAM).

## Phase 6 - Watch mode (Oct 28) - DONE
- Sources behind one frames() interface: FileSource (real, OpenCV), RtspSource (OpenCV), PhoneSource stub with TODO(TEAM) for the phone endpoint choice.
- Room guard in code: bathrooms always refused with the product wording; bedrooms require resident consent (API returns 422; RTSP URLs never listed).
- Camera health (dark/uniform/frozen/moved), running-average change detection, model-call gate (min interval + hourly cap + daily budget via CostGuard).
- State machine + engine: duration rules sustain-then-alert exactly once per episode (tests: 40s open = 1 alert; flapping = 0; two episodes = 2), deadline rule alerts once, dark frames move to CANNOT_SEE and recover.
- API: sources CRUD-lite, POST /watch/demo-run compiles a sentence and runs the real engine on a scripted timeline, GET /watch/events. Frontend: WatchSetup (guard wired) + WatchLive (state timeline, alert count).

### Next
Human review of schemas, packs and skeleton. On approval: Phase 1 (capture) and Phase 2 (scan pipeline on mocks), workers per spec section 16.
