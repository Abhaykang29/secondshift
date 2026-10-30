# Live Verification Log

Rule (pass 2): a feature is "done" only when it has run against the real
Meta API on real footage from `data/inbox/`, recorded here by
`scripts/verify_live.py`. Mock results never count. Each entry records:
check, date/time, model IDs, input file (name only), what was produced,
pass/fail vs the acceptance criterion, cost (ledger), duration.

| Check | Phase | Status |
|---|---|---|
| smoke | B | PARTIAL — Spark/Wonder/SAM/Image reachable live 2026-10-28; Voice Transcribe NOT reachable (endpoint unlocated) |
| ledger | B | PASS 2026-10-28 — recorded call costs $0 on repeat (cache_hit), SQLite total persists across reopen |
| replay_offline | B/K | PARTIAL — transport replay raises CacheMiss on unrecorded steps (unit-tested); full recorded flow lands in Phase K |
| scan_falls | E | NOT RUN — no real footage yet (a synthetic-footage live run on 2026-10-28 does NOT satisfy this; Rule 5) |
| blur | E | CODE BUILT, NOT VERIFIED - privacy/blur.py (SAM person blur + blur-all-but fallback) unit-tested on synthetic frames; live check needs falls_routine.mp4 |
| visualize | F | CODE BUILT, NOT VERIFIED - crop-edit-composite Muse Image path + mock stamp unit-tested with stub editors; live check needs a real scan |
| recheck | E | CODE BUILT, NOT VERIFIED - contested-item judge wired (prompts/recheck_judge.md); live check needs falls_recheck.mp4 |
| rules_unseen | D | REPORTED — v1 (blind): App B status 37/40, prim 6/16; unseen status 23/30, prim 4/16. After ONE documented prompt iteration (v2: hazard-side primitive semantics): App B status 38/40, prim 15/16; unseen status 26/30, prim 15/16. The unseen set is blind only for v1 |
| watch_gate_live | G | CODE BUILT, NOT VERIFIED - LiveWatch loop (hub frames -> health -> change -> gate -> SAM + Spark state judge -> state machine -> store + SSE) unit-tested on synthetic frames (1 alert, cannot_see, recovery); live check needs a real phone + gate |
| watch_cover | G | CODE BUILT, NOT VERIFIED - covered-frame path unit-tested (CANNOT_SEE event); live timing check pending |
| voice | H | NOT RUN — blocked on docs/meta_get_code/audio.txt |
| packs_all | I | NOT RUN - 7 packs now (mosquito_breeding added 2026-10-29, pet_safety excluded from the demo by team decision); live runs need the walkthrough files |
| eval_real | J | NOT RUN |

## Entries

<!-- verify_live.py appends entries below this line -->

### smoke — PARTIAL (2026-10-29T03:37:57Z)
- detail: muse-spark-1.3: OK (usage={'completion_tokens': 737, 'prompt_tokens': 11, 'total_tokens': 748, 'completion_tokens_details': {'reasoning_tokens': 726}, 'prompt_tokens_details': {'cached_tokens': 0}}); muse-wonder-1.0: OK (usage={'completion_tokens': 122, 'prompt_tokens': 11, 'total_tokens': 133, 'completion_tokens_details': {'reasoning_tokens': 112}, 'prompt_tokens_details': {'cached_tokens': 0}}); sam-3.1: FAIL ProviderUnavailable: Meta API /responses returned HTTP 400: {"error":{"code":null,"message":"invalid image data at input[0].content[1]: the `image/jpeg` payload could not be decoded (it may be corrupt or truncated).","param":null,"type":"invalid_request_error"}}; muse-image-1.0: OK (verified 2026-10-28: generations + edits shapes); muse-voice-transcribe-1.0: FAIL endpoint unlocated (see Phase H; needs playground Audio snippet)
- cost: see ledger (Phase B)
- duration: 9.1s

### smoke — PARTIAL (2026-10-29T03:38:13Z)
- detail: muse-spark-1.3: OK (usage={'completion_tokens': 217, 'prompt_tokens': 11, 'total_tokens': 228, 'completion_tokens_details': {'reasoning_tokens': 207}, 'prompt_tokens_details': {'cached_tokens': 0}}); muse-wonder-1.0: OK (usage={'completion_tokens': 135, 'prompt_tokens': 11, 'total_tokens': 146, 'completion_tokens_details': {'reasoning_tokens': 125}, 'prompt_tokens_details': {'cached_tokens': 0}}); sam-3.1: OK; muse-image-1.0: OK (verified 2026-10-28: generations + edits shapes); muse-voice-transcribe-1.0: FAIL endpoint unlocated (see Phase H; needs playground Audio snippet)
- cost: see ledger (Phase B)
- duration: 8.0s

### ledger — PASS (2026-10-29T03:42:07Z)
- detail: first call $0.0022; repeat cache_hit=1 actual=$0.0000; total after DB reopen $0.0022
- cost: see ledger (Phase B)
- duration: 3.8s

### rules_unseen — REPORTED (2026-10-29T03:58:41Z)
- detail: Appendix B status 37/40, primitives 6/16; unseen status 23/30, primitives 4/16; pass2 ledger total $0.50; compiler rule_compiler@v1:spark:muse-spark-1.3
- cost: see ledger (Phase B)
- duration: 399.0s

### rules_unseen — REPORTED (2026-10-29T04:06:05Z)
- detail: Appendix B status 38/40, primitives 15/16; unseen status 26/30, primitives 15/16; pass2 ledger total $1.03; compiler rule_compiler@v1:spark:muse-spark-1.3
- cost: see ledger (Phase B)
- duration: 393.1s

### reasoning_effort — REPORTED (2026-10-29, manual entry)
- detail: reasoning_effort="low" on compile+judge. Appendix B rerun LIVE: status 38/40, primitives 15/16 - identical accuracy to the v2 baseline; latency mean 3.87s/call (p50 3.88s, max 6.19s) vs ~5.6s baseline (~30% faster). 22 live calls, $0.12. Decision: keep "low".
- cost: $0.12 (phase_tag pass2-re)
- duration: 87s

### smoke_test_1 — REPORTED (2026-10-29, manual entry; NOT official footage)
- detail: user-supplied unstaged home tour (data/inbox/test_1.mp4, 55s, 80 keyframes) scanned live, falls+fire+pets, CACHE_MODE=record. 5 confirmed (floor cord, rug, extinguisher absent, pet cords x2), 1 needs_human (toxic plant - judge spotted the succulent despite SAM miss), 4 rejected, 43 area-level cannot_assess (rooms never filmed). Person blur ran on all 80 keyframes; person-heavy frames spot-checked blurred. Afters: cord subtle/plausible; rug evidence frame poorly chosen (dining shot); extinguisher absence edit BROKEN (glitch strip - real Phase F absence-region bug). Two rejections look wrong on frame inspection (pet bowls visible at 25.5s; stove + towels visible) - awaiting user marks on docs/reviews/smoke_test_1_review.html.
- cost: $0.94 (178 calls: 157 SAM, 18 vision, 3 image)
- duration: 640s wall

### smoke_test_1_rerun — REPORTED (2026-10-29, manual entry; NOT official footage)
- detail: same test_1.mp4 re-run after the 9 smoke-test pipeline fixes (commit 0cfbd1c, 113 tests). Scan 127s (was 605s; target <180s met), wall 159s, $0.58 new spend (85/124 SAM calls cache hits; propose went live once because payloads now label images). Findings: toxic plant needs_human -> confirmed (SAM, right frames now searched); extinguisher confirmed -> needs_human "Not visible, may be stored out of sight." (fix 5); bed-light rejected -> confirmed; pet cords x2 confirmed; cannot_assess 43 -> 17; evidence timestamps are real frame times (7.0/16.0/24.0/29.5/46.0). Absence-edit glitch strip GONE (bed-light after is coherent); remaining viz weakness is model behavior: "move/add" edits paint a miniature scene into the crop (plant, bed-light) instead of transforming the object. Run variance noted: the live propose pass did not propose the living-room floor cord this run, and proposed the small red pet-bowl mat as the rug finding (fix 9 semantics) - a from-cache replay of the same keyframes yields 6 hazards incl. that mat confirmed. Review sheet: docs/reviews/smoke_test_1_run2_review.html.
- cost: $0.58 (phase_tag pass2-smoke2)
- duration: 159s wall

### smoke_test_1_run3 — REPORTED (2026-10-30, manual entry; NOT official footage)
- detail: test_1.mp4 after the two-way check + propose stability + edits fix (commit b2a1e76, 120 tests). Recall vs the user's 8 ground-truth items: 6/8. Caught: TV cords, desk cords, plant, no bedside lamp, extinguisher (needs_human cap), pet bowls + red mat by the balcony door (BOTH via the new SAM sweep - the sweep's first catches). Missed: living-room floor cord as FALL-FLOOR-CORD (living-room cords caught only as PET-CORDS) and towels on the oven handle (FIRE-STOVE-COMBUSTIBLES never proposed; sweep did not surface it). Both misses are thin/elongated objects on wide frames. Also correct: FALL-FLOOR-RUG (living) rejected with fix-9 reasoning ("large area rug anchored by coffee table, no curled edges"). Temperature 0 accepted by the API (probed) and used for propose - $0 increase. Edits: planner-named instructions + context crops verified in-pipeline (plant removal clean, lamp experiment placed the lamp on the real glass side table). CA 17 -> 12. Scan 364s / $1.10 this run - slower than run 2 because the temperature change invalidated the propose cache and the sweep added ~120 mostly-uncached SAM calls (309 segmenter calls total, 105 hits); steady-state sweep cost is capped at 100 SAM calls/scan.
- cost: $1.10 (phase_tag pass2-smoke3)
- duration: 395s wall

### pass3_p1_test1 — REPORTED (2026-10-30, manual entry; NOT official footage)
- detail: Pass 3 P1 acceptance on test_1.mp4 (falls+fire+pets), final P1 code. Cold run (fresh CACHE_DIR): recall 7/8 vs the team's ground truth, precision 8/8 reported findings (6 confirmed + 2 needs_human, every one a ground-truth item; the earlier cold run had one duplicate stove report, 8/9). Warm re-run on the same cache: identical findings, scan 78s (target <= 90s MET), $0.12. Cold scan 368s (target <= 240s MISSED - 281 live calls: 253 segmenter incl. tiles/sweep, 26 vision, 2 edits), cold cost $1.22. Only miss: FALL-FLOOR-CORD as its own falls item (thin white cable on light flooring defeats SAM even on floor-band tiles; the same cords ARE reported as PET-CORDS-CHEWABLE carrying falls+fire+pet pack tags via cross-pack attribution). Towels on the oven handle now recalled (propose path; the proximity sweep covers it when propose misses). No "other" rooms (desk nook smoothed to bedroom). CA count varies by run (10-18) with propose variance.
- cost: $1.22 cold + $0.12 warm (phase_tag pass3 / pass3-warm)
- duration: 368s cold scan, 78s warm scan

### pass3_p2_packs — REPORTED (2026-10-30, manual entry; test_1.mp4 only, NOT official footage)
- detail: Pass 3 P2 - 10 packs / 110 items load and validate. One live scan per new pack on test_1.mp4: home_safety_inspection (156s) correctly capped HOME-EXTINGUISHER-ABSENT at needs_human with the standard wording and produced a planner-rewritten visualization; workplace_safety (213s) capped WORK-EXTINGUISHER-ABSENT at needs_human in two rooms, honest rejections elsewhere (a home is not a workplace); car_seat_check (77s) is a correct true negative - no vehicle interior, nothing confirmed, SEAT-OBJECTS-LOOSE honestly rejected. SEAT-TIGHTNESS always lands as cannot-assess with the exact shake-test wording (a first run showed a generic propose entry winning; the pipeline now normalizes it - verified on a 13s warm re-run). pet_safety is back in the demo set per the Pass 3 brief.
- cost: ~$1.95 across the four runs (phase_tag pass3; pass-3 total $4.39 of $50 after P2)


## Pass 3 P4 - engine layer + bring-your-own-checklist (2026-10-30)

- entry_id: pass3_p4_engine
  - core/ package: compile_checklist (packs + custom), check, recheck,
    compile_rule, live - domain-agnostic; an AST-level test enforces
    that nothing in core/ imports the app layer. docs/ENGINE.md
    documents the interface, the /v1 REST API (API keys, 30/min rate
    limit, the shared cost guard) and the roadmap list.
  - Live compile (Spark, checklist_compiler v1): 5 lines in -> 4 items
    (cords presence/thin, plant presence, towels presence/thin,
    extinguisher absence with anchors [front door, wall by front
    door]) and 1 honest refusal ("extinguisher bracket screwed tight"
    -> "Video cannot tell if the bracket screws are tight so check
    them by hand instead.").
  - Live run of the compiled custom-942b3dca on test_1.mp4: towels
    CONFIRMED in the kitchen; cords CONFIRMED in living room and
    bedroom (TV + desk cords), honestly rejected in the kitchen;
    plant REJECTED (a recall miss - the pack item finds it; the
    compiled draft's context is thinner; recorded, not hidden);
    extinguisher absence -> CANNOT ASSESS (the front-door anchor was
    not clearly filmed, so no fake needs-human). One duplicate:
    towels also reported under "living" (room-attribution split).
  - /v1 verified via TestClient: 401 without a key, checklist compile
    200 with the local key, OpenAPI at /v1/openapi.json; the 429 rate
    limit is covered in tests. Pass-3 spend after P4: $5.17 of $50.


## Pass 3 P5/P6 - routine + voice decisions, ablations, demo prep (2026-10-30)

- entry_id: pass3_p6_eval_demo
  - Routine (P5): NOT DONE live, hidden on purpose. The live scan
    consumes routine contacts only from the scripted demo scenario;
    the geometry (pipeline/routine.py) and Wonder summaries are
    unit-tested but no feeder turns a real routine clip into boxes,
    and no team routine clip exists in data/inbox to verify one
    against. The app's optional routine step is HIDDEN (both copies
    removed from CheckupNew) rather than left as a dead control.
    Unblock: one fixed-camera routine clip + the SAM feeder build.
  - Voice: audio.txt never arrived and the transcribe endpoint was
    never located (Pass 2 H). No voice UI exists to remove - the
    Learn tab states plainly that Muse Voice is not connected and
    narration is not transcribed. Nothing in the demo script
    mentions voice.
  - Ablations (scripts/run_ablation.py, in-process on the acceptance
    capture's keyframes, falls+fire+pets, the 8 ground-truth items,
    P1 scoring convention): full (sweep + thin tiles) recall 7/8
    family (6/8 strict), precision 6/9, 112s. no-sweep: recall 7/8,
    precision 6/8, 5s (propose fully cache-warm). no-thin: recall
    7/8, precision 6/8, 20s. Read honestly: (1) on this video the
    sweep added NO recall today and one out-of-family report - yet
    in run 3 it was the sweep that caught the pet bowls; today NO
    config caught them. Run-to-run variance is the same size as the
    sweep's contribution at n=1 video. (2) The thin tiles did not
    rescue the floor cord in any config - SAM cannot segment that
    cable even tiled. (3) The sweep costs ~+100s and ~90 SAM calls
    per scan when live. Conclusion recorded, not hidden: the two-way
    check is unproven at n=1; more labeled clips are the only cure.
    Ablation spend $0.64 (ledger tag pass3-ablation).
  - Demo: scripts/demo_check.py rewritten around the guarantees
    that actually hold - run_demo.py's recorded mock-scenario replay
    (parent 9 confirmed, recheck 32.1 -> 78.2, watch alert fires,
    baby 7 confirmed, refusal + 3 alternatives) and the app demo
    flow in mock mode. `make demo-check` passes 3/3 offline. FOUND
    AND DOCUMENTED: replaying a real recorded scan through a fresh
    upload is NOT bit-exact - person-blur output varies slightly
    between runs (a handful of frames per capture), changing image
    hashes and cache keys; all 7 propose batches of the acceptance
    capture miss today. The real fallback is the stored reports
    themselves (they open with zero provider calls). DEMO_SCRIPT.md
    rewritten to the Pass 3 structure with these fallbacks stated.
  - Pass-3 live spend, final: $5.70 of the $50 cap (tags pass3
    $5.06 + pass3-ablation $0.64). All-time ledger $10.79.
