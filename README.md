# SecondShift

**SecondShift — a safety check for the places people live and work.
Film a walkthrough, get the hazards with proof, honest "can't tell"
answers, and a re-check that confirms the fix.**

An installable phone app (PWA) built on a reusable checking engine:
a checklist in plain English plus a video goes in; evidence-backed
verdicts — yes / no / can't tell — come out.

- **Check (the check-up).** Film a 2–3 minute walkthrough (phone, or
  Ray-Ban Meta glasses: "Hey Meta, take a video", then import). Pick
  up to 3 of 10 checklists — older adults (falls, the hero), baby-
  proofing, home safety inspection, workplace safety, pets, fire
  safety, car seat check, earthquake ready, home from hospital,
  mosquito breeding — or type your own. Every reported hazard carries
  its evidence frame and SAM box, a fix plan, and a watermarked
  "after" visualization; things a camera cannot settle say so
  ("needs a human look", "couldn't check"). Fix, re-film, and the
  re-check diffs the two scans: Resolved ✓ / Still there / New /
  Couldn't tell, with the home score before → after.
- **Live Check (opt-in; a phone pointed at one spot).** Type a rule
  in plain English — "tell me if the front door opens at night" —
  and it compiles into a verifiable rule, or refuses honestly and
  offers alternatives ("warn me before Mom falls" is refused: a
  camera can't know that). Rules answer MET / NOT MET / CANNOT TELL,
  bathrooms are always refused, bedrooms need the resident's consent,
  and no video is saved.
- **Bring your own checklist.** Type 3–10 lines in your own words;
  each compiles into a checkable item or a refusal with a reason.
  Labelled "Custom checklist — not reviewed by an expert".

Core principle: **check spaces, not people.** People are blurred in
every frame before any model reads them.

## Quickstart

```bash
make setup       # backend venv + frontend deps
make dev         # backend :8000, frontend :5173
make check       # lint + types + tests (132)
make demo        # the app in demo configuration (scripted demo, offline)
make demo-check  # proves the demo paths work offline (run it 3x)
```

Default provider is `mock` — the full app works end to end with no
API keys. Live mode resolves the Meta key from the environment or
the local vault connector; see `docs/LIVE_VERIFICATION.md` for what
is verified live and what is not.

## Install on iPhone

Serve the app over HTTPS (`make dev-https`, or a tunnel such as
`npx localtunnel --port 5173`), open it in Safari, then Share →
Add to Home Screen. Details in `frontend/PWA_NOTES.md`.

## The engine layer

The app is one client of `secondshift.core` — `compile_checklist /
check / recheck / compile_rule / live` — with a REST API at `/v1`
(API keys, rate limits, OpenAPI at `/v1/openapi.json`). See
`docs/ENGINE.md`.

## Honest limits

SecondShift is a screening tool, not a medical device or an
emergency alarm. It can miss things — on the one real walkthrough we
could label, it found 7 of the owner's 8 hazards; a thin white cable
on light flooring defeated SAM even in close-up crops. It cannot
test tightness, alarms, or anything out of sight: a car seat's
tightness gets the 1-inch shake-test line, not a verdict. Voice is
not connected (the transcription endpoint was never located), and
the routine analysis runs only in the scripted demo — the live
routine step is hidden until a team routine clip exists to verify
it against.

## Data note

Occasional snapshots are sent to Meta's AI models to check them. This runs on Meta's free hackathon credits; Meta says content sent on free credits may be used for product improvement. We only process footage from people who agreed to that. (CREDITS_MODE=free, the default. On paid Standard-tier credits - CREDITS_MODE=paid - Meta's Standard terms apply instead.) We don't claim zero retention. Raw video is deleted after processing unless you choose to keep it. See `docs/PRIVACY.md`.

## Impact facts

Only the sourced facts in `docs/IMPACT.md` are used anywhere in this product.

## Built with

Built with Muse Code (Muse Spark 1.3). Meta models: Muse Spark 1.3
(propose, judge, rule + checklist compilers), SAM 3.1 (verification,
sweep, person blur), Muse Image ("after" visualizations), Muse
Wonder (routine summaries, scripted demo). Muse Voice Transcribe is
NOT connected — its endpoint could not be located.
