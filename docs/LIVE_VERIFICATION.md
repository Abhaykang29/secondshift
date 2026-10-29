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
