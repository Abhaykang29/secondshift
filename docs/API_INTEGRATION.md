# API integration runbook - "keys arrived" (target: live in under 3 hours)

Everything outside `backend/secondshift/providers/meta/` is already built,
tested, and running on mocks. When `META_API_KEY` arrives, this is the
whole job. Estimated times assume the best-known shapes in the adapters
are mostly right; every unverified detail is marked `TODO(API)` in code.

## Timeline
- 0:00-0:15 - Step 1: key in, smoke test run, real shapes captured.
- 0:15-1:00 - Step 2: fix adapters until the smoke test is green.
- 1:00-1:30 - Step 3: measure image tokens; update cost estimates.
- 1:30-2:15 - Step 4: one real video end to end; tune thresholds.
- 2:15-2:45 - Step 5: record the demo runs.
- 2:45-3:00 - Step 6: switch demo mode to replay; final check.

## Step 0 - Put the key in (2 min)
```bash
cp .env.example .env   # if .env doesn't exist yet
# set META_API_KEY=<the key> in .env  (never commit .env; it is gitignored)
```

## Step 1 - Run the smoke test (10 min)
```bash
make smoke-meta
```
It makes one tiny call per model and prints the ACTUAL response shape per
adapter. Save that output - Step 2 works from it. If a call 401s, the key
or the auth header is wrong (TODO(API) in `text_vision.py` - check
dev.meta.ai for the current auth scheme). If it 404s, the base URL/path
constants at the top of `text_vision.py` are the fix.

## Step 2 - Fix the adapters (30-45 min)
Only files under `backend/secondshift/providers/meta/` may change.
The normalizers are already unit-tested on sample payloads
(`tests/test_meta_normalizers.py`); for each mismatch between a sample
payload and the real shape printed in Step 1:
1. Add the REAL payload (redact nothing but the key) as a new fixture case
   in `tests/test_meta_normalizers.py`.
2. Adjust the matching normalizer (`normalize_chat_content`,
   `normalize_sam_response`, `normalize_image_response`,
   `normalize_transcript`) until the new test passes.
3. SAM specifics: if masks arrive as RLE, implement the decode in
   `normalize_sam_response` where the loud `ValueError("TODO(API): RLE...")`
   is - the test `test_sam_normalizer_rejects_rle_loudly` tells you the spot.
4. Implement the remaining transport stubs in order: `MetaSegmenter.segment`,
   `MetaTranscriber.transcribe`, `MetaImageEditor.edit` - each currently
   raises with a pointer to its ready normalizer.
5. Verify no `*-contributor` model id appears anywhere:
   `grep -rn contributor backend/ --include=*.py | grep -v ALLOW_CONTRIBUTOR` must be empty outside eval/rules.
Done when: `make smoke-meta` prints OK for spark + sam, and `make check` is green.

## Step 3 - Measure image tokens, update costs (30 min)
The price table assumes 1,500 image tokens per image (spec section 11.4).
Measure the truth: the smoke response's usage block (TODO(API): field
name) reports prompt tokens for the 1-image call; subtract the text-only
call's prompt tokens to get tokens-per-image at our keyframe size.
Then update, in `backend/secondshift/config.py`: `TOKENS_PER_IMAGE_ESTIMATE`
and any price corrections in `PRICE_TABLE`. Re-run `scripts/estimate_costs.py`
and confirm a full scan estimate stays in the $0.15-$0.50 band; if not,
lower `MAX_KEYFRAMES` before touching anything else.

## Step 4 - One real video, tune thresholds (45 min)
1. `PROVIDER=meta CACHE_MODE=record make dev`; create a check-up and
   upload one real walkthrough (TODO(TEAM): Person A's footage).
2. Read the report like a skeptic: every confirmed hazard must be visible
   in its evidence frame. Note false confirms and misses.
3. Tune ONLY these, in `.env`, in this order: `MIN_MASK_SCORE` (raise to
   cut false confirms), `SHARPNESS_MIN`/`SCENE_CHANGE_MIN` (keyframe
   quality/coverage), `VERIFY_FRAMES` (more frames = fewer absence misses).
4. Re-run the same video; the second run must be visibly better, not just
   different. Log before/after in `PROGRESS.md`.

## Step 5 - Record the demo runs (30 min)
With the tuned settings, run the full demo script (docs/DEMO_SCRIPT.md)
once with `CACHE_MODE=record`. The recordings land in `fixtures/recordings/`
and make the demo deterministic and free to repeat.

## Step 6 - Switch to replay (5 min)
`make demo` already sets `PROVIDER=meta CACHE_MODE=replay`. A replay miss
is an error by design (it must never silently call the live API on stage).
Final gate: `make check` green + one full `make demo` run with WiFi off.

## If something is not in this runbook
The answers are in code, marked: `grep -rn "TODO(API)" backend/` lists
every unverified assumption in one place. Fix the marker, add the fixture
test, remove the marker.
