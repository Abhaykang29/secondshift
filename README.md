# SecondShift

**SecondShift helps families make a home safer for the people most likely to get hurt in it - older adults (falls) and babies/toddlers (babyproofing) - using one phone and Meta's AI models.**

- **Mode 1 - Check-up (default; no camera stays in the home).** Film a 2-3 minute walkthrough. SecondShift returns a ranked, evidence-backed list of hazards, each with an evidence outline (SAM box-verified), a plain-language fix plan, "after" visualizations (today: locally drawn overlays on the evidence frame - real Muse Image edits are pass 2 Phase F), and a monthly re-check.
- **Mode 2 - Watch (opt-in; one cheap camera pointed at one spot).** Type a rule in plain English. SecondShift compiles it into a verifiable rule - or refuses it and offers observable alternatives. Every rule answers **MET / NOT MET / CANNOT TELL**.

Core principle: **check spaces, not people.**

> Professional home-safety visits work, but they're scarce. SecondShift gives every family a check-up in five minutes - and the honesty to say what it can't see.

## Quickstart

```bash
make setup   # backend venv + frontend deps
make dev     # backend :8000, frontend :5173
make check   # lint + types + tests
make demo    # demo mode: replays recorded MOCK runs offline today - true recorded-real replay is pass 2 Phase B/K (see docs/LIVE_VERIFICATION.md)
```

Default provider is `mock` - the full app works end to end with no API keys.

## Honest limits

SecondShift is a screening and awareness tool. It is not a medical device, not an emergency alarm, not a replacement for an occupational therapist or a professional babyproofer, and it cannot guarantee anything is safe.

## Data note

Occasional snapshots are sent to Meta's AI models to check them. This runs on Meta's free hackathon credits; Meta says content sent on free credits may be used for product improvement. We only process footage from people who agreed to that. (CREDITS_MODE=free, the default. On paid Standard-tier credits - CREDITS_MODE=paid - Meta's Standard terms apply instead.) We don't claim zero retention. Raw video is deleted after processing unless you choose to keep it. See `docs/PRIVACY.md`.

## Impact facts

Only the sourced facts in `docs/IMPACT.md` are used anywhere in this product.

## Built with

Built with Muse Code (Muse Spark 1.3) - see `BUILD_LOG.md`. Meta models: Muse Spark 1.3, Muse Wonder, SAM 3.1, Muse Image (see spec section 6 for each model's job). Muse Voice Transcribe is NOT connected yet - its endpoint could not be located (pass 2 Phase H, needs the playground Audio snippet).
