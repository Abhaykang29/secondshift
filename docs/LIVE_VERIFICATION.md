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
| blur | E | NOT RUN |
| visualize | F | NOT RUN |
| recheck | E | NOT RUN |
| rules_unseen | D | NOT RUN |
| watch_gate_live | G | NOT RUN |
| watch_cover | G | NOT RUN |
| voice | H | NOT RUN — blocked on docs/meta_get_code/audio.txt |
| packs_all | I | NOT RUN |
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
