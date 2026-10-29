# SecondShift — Status Report
**Date:** Wednesday, October 28, 2026 (evening, EDT)
**Repo:** github.com/Abhaykang29/SecondShift — `main` @ `2b0503a` (pushed and verified)
**Tests:** `make check` green — 78 tests (pytest, ruff, mypy --strict, tsc, eslint)
**Submission deadline:** Nov 4, 2026, 9:00 PM ET (submit by afternoon)

## What SecondShift is
A home-safety screening tool: one phone walkthrough → SAM-verified, ranked
fall/babyproofing hazards with fix plans and a printable/shareable report
(Check-up), plus an opt-in Watch mode where plain-English rules are compiled
or refused with alternatives. Check spaces, not people. Screening tool, not
a medical device or emergency alarm — those limits are stated in the product.

## Done — the build (Phases 0–8, all committed and pushed)
- **Phase 0 — Contracts:** domain schemas, falls pack (16 items), babyproofing
  pack (13), fire-safety pack (6, data-only), provider interfaces,
  mock/cache/cost-guard, all 14 frontend routes, 10 prompt templates,
  Appendix B 40 rule-sentences as eval fixtures.
- **Phase 1 — Capture:** video probe (friendly >6 min rejection), ffmpeg
  frame extraction, sharpness/brightness quality gates, keyframe selection
  (real upload produced 58 keyframes, inside the 40–80 spec range),
  synthetic walkthrough generator.
- **Phase 2 — Scan pipeline:** propose → verify (presence / absence /
  measurement / interaction) → routine-path geometry → dedupe → rank with
  the exact §9.7 formula. Locked snapshot: 9 confirmed + 1 SAM-rejected
  false positive, deterministic.
- **Phase 3 — Fixes & report:** fix planner chooses only from pack
  libraries, watermarked visualizations ("Visualization — not a photo"),
  report JSON + printable HTML + WhatsApp share text, fix tracker,
  phone-width (390px) UI with real report pages, screenshots in
  `docs/screenshots/`.
- **Phase 4 — Re-check + rules:** re-check diff with documented score
  formula, plain-English rule compiler (Appendix B 40/40 in tests, every
  refusal offers alternatives), observability precheck.
- **Phase 5 — Eval harness:** 4 ablation configs on mock labels — SAM
  lifts precision 0.94 → 1.0; /eval page renders runs. All numbers are
  labeled mock (harness validation, not product accuracy).
- **Phase 6 — Watch:** room guard in code (bathrooms always refused,
  bedrooms need resident consent), camera health checks, change detection,
  model-call gating, state machine — proven: a 40s open gate produces
  exactly 1 alert; flapping produces 0.
- **Phase 8 — Demo mode:** full demo proven end-to-end through
  record/replay with WiFi-off capability; Settings (incl. working
  "delete everything"), Ask page, accessibility pass.

## Done — finish pass (Oct 28 evening)
- Real **PhoneSource**: phone browser page at `/camera` streams frames
  over a WebSocket into an in-memory hub; `make dev-https` serves local
  HTTPS so iPhone Safari allows the camera.
- **"MOCK DATA" watermark** on /eval (badge + diagonal overlay).
- **Pre-commit guard** (`.githooks/pre-commit`): blocks media, recordings,
  `data/`, and `.env` from commits (exceptions: demo-cache, docs
  screenshots). Tested live — it trips.
- **MIT LICENSE** (repo version carries Abhay's copyright line).
- **BUDGET_USD=140** default.
- **CREDITS_MODE=free|paid** (default free): README, PRIVACY.md, and the
  in-app data note carry the verbatim free-credits sentence ("This runs on
  Meta's free hackathon credits; Meta says content sent on free credits
  may be used for product improvement. We only process footage from people
  who agreed to that."); the "not used for training" claim removed from
  free-mode copy.
- TODO(TEAM) list trimmed (Appendix E item deleted).

## Done — Phase 7, LIVE Meta API integration (Oct 28 evening)
Credential: Meta Model API key stored in the secure vault (connector
`custom.meta-ai`); the app resolves an env key or the vault surrogate —
the real key never enters the process or any file. No billing or
payment-method errors at any point.

Verified against the live API:
- `GET /v1/models` — 200. Model IDs match config exactly: muse-spark-1.3,
  muse-wonder-1.0, sam-3.1, muse-image-1.0, muse-voice-transcribe-1.0.
  Contributor variants exist and are never called (hard rule).
- **Chat/vision** — `POST /v1/chat/completions`, OpenAI-style messages
  with image_url data URIs, usage block returned. Measured image cost:
  ~110 tokens (320×240), ~1,200 tokens (1280×720) → cost estimate updated
  to 1,200/keyframe. Note: Spark spends most output tokens on reasoning.
- **SAM 3.1** — served ONLY on `POST /v1/responses` (chat endpoint
  refuses it). Output text carries `<|box;x1;y1;x2;y2;w;h|>` segments;
  the probe box was **pixel-exact**. Billed per image processed
  (usage.images_processed), no confidence score returned — the adapter
  uses a documented constant score. The pixel-mask string encoding is
  NOT decoded yet; boxes drive verification geometry in v1.
- **Muse Image** — generations and edits verified
  (`POST /v1/images/edits` with JSON `images[].image_url`), returns
  data[0].b64_json (WebP).
- **Smoke test** — `make smoke-meta` passes end-to-end through the app's
  own adapters (chat OK with real usage, SAM segment OK).

**First real pipeline run** (synthetic walkthrough, PROVIDER=meta,
CACHE_MODE=record, driver `scripts/run_real_scan.py`): completed in
**164 s**. The live model proposed 7 hazards:
- 2 **confirmed** — objects on stairs; floor clutter (judge fallback)
- 2 **needs human** — hallway rug; furniture support
- 2 **rejected** by verification — floor cord; kitchen high storage
- 1 **cannot assess** — bathroom grab bar ("didn't see the toilet clearly")
- 4 fix cards built from the pack libraries.

Adapter hardening driven by live model behavior (all with tests):
proposal field coercion (the model sometimes omits sam_prompts /
confidence / why_risky) and cannot_assess coercion (bare item_ids →
schema). Transport is stdlib urllib — httpx misparses this
environment's NO_PROXY list.

## Known gaps (honest list)
1. **Muse Voice Transcribe** — endpoint not located after 4 documented
   probes (audio/transcriptions 404; chat/responses model_not_found).
   Narration is optional; scans proceed without it.
2. **Visualizations = 0** on the real path (mock path produces them) —
   candidate-filter issue; fix before demo day.
3. **Cost ledger reads $0.00** for live calls — adapter usage is not yet
   wired into the ledger. Actual spend so far: probes + one full scan,
   a few dollars at most; an exact figure awaits that wiring.
4. **SAM pixel masks** not decoded (proprietary encoding) — boxes only;
   on cartoon synthetic frames SAM returned no boxes and confirmations
   came from the judge fallback. Real-footage behavior untested.
5. **Recordings cache** did not capture live meta calls — replay cache
   for real runs is not yet a thing.
6. All eval accuracy numbers remain **mock-labeled** until human-labeled
   real captures exist.

## Still needs a human (TODO(TEAM), in demo order)
1. Real footage: consented parent-home + baby-home walkthroughs
   (`data/inbox/test_walkthrough.mp4` still not on this machine).
2. Human labels for 20–30 captures.
3. Babyproofing statistics sourcing (CPSC/AAP) — placeholders remain
   TODO(STAT), never invented.
4. Hindi native review; pa/es/fr/zh/ar translations.
5. Clinician/OT review of packs, severities, fix steps.
6. Phone-endpoint choice for PhoneSource is settled (/camera WebSocket);
   counsel review of PRIVACY.md remains.

## Security notes
- GitHub push used a PAT the user pasted in chat after the secure page
  failed three times on his end ("connection is invalid"); used
  transiently only, never stored — user advised to revoke/rotate it.
- Pushed tree verified clean: 243 files, no `.env`, media, `data/`, or
  recordings beyond the intended demo cache.
