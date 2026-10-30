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
