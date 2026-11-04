# SecondShift

[![CI](https://github.com/Abhaykang29/SecondShift/actions/workflows/ci.yml/badge.svg)](https://github.com/Abhaykang29/SecondShift/actions/workflows/ci.yml)

**SecondShift turns plain-English rules into checks a camera can
run, and answers each with Yes, No, or Can't tell — plus the proof.**

## Quickstart (3 commands)

```bash
make setup    # 1. backend venv + frontend deps
make doctor   # 2. checks your machine; every problem prints its exact fix
make demo     # 3. the app, running on stored reports - no key needed
```

- **No key needed** for `make demo`: it replays stored reports and
  the scripted demo, fully offline.
- **A Meta API key is needed only for live scans** (a new video
  analysed on the spot): `cp .env.example .env`, set `META_API_KEY`,
  then run `PROVIDER=meta make dev`. `make check` (lint + types +
  tests) and `make demo-check` (offline demo proof) need no key.
- **Videos are processed by Meta's API** — frames from a live scan
  are sent to Meta's models (Muse Spark, SAM) for analysis; people
  are blurred in every frame first. Nothing is sent anywhere in
  demo mode.

A safety check for the places people live and work: film a
walkthrough, get the hazards with proof, honest "can't tell"
answers, guided re-film instructions for whatever the camera
missed, and a re-check that confirms the fix. The numbers behind
its accuracy live in `eval/HONESTY.md` (computed from stored
results by `scripts/honesty_report.py`).

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

## Going further

```bash
make dev         # backend :8000, frontend :5173 (PROVIDER=meta for live scans)
make check       # lint + types + tests
make demo-check  # proves the demo paths work offline (run it 3x)
```

Default provider is `mock` — the full app works end to end with no
API keys. Live mode resolves the Meta key from the environment,
`.env`, or the local vault connector; see
`docs/LIVE_VERIFICATION.md` for what is verified live and what is
not, and `docs/ROBUSTNESS.md` for how odd videos are handled.

## Use it on your phone

```bash
make phone            # same Wi-Fi
make phone TUNNEL=1   # Wi-Fi isolates clients (offices, venues)
```

One command builds the frontend and serves the **whole app from the
backend** over HTTPS at `https://<this-machine's-LAN-IP>:8000`, and
prints that URL with a QR code in the terminal — scan it and the
full app opens on the phone, no app store, no separate dev server.
The certificate is generated on the spot with the machine's current
LAN IP in it; the phone will show a one-time certificate warning
(tap Advanced → Proceed). For the **camera on iPhone**, iOS may
also require trusting that certificate (Settings → General → About
→ Certificate Trust Settings) — the `TUNNEL=1` variant avoids this:
it opens a temporary Cloudflare tunnel with a normally trusted
HTTPS address. **Warning: anyone with the tunnel link can use your
API credits while it is open — stop it when you are done (Ctrl+C).**
If `cloudflared` is not installed, the command prints how to
install it and keeps serving on the LAN.

The Meta API key stays on this machine (environment or `.env`); it
is never sent to the browser. When a key is configured, `make phone`
serves in live mode automatically (`PROVIDER=mock make phone`
forces demo mode); with no key configured, the app loads in demo
mode and the Check and Live screens say so plainly.

## Install on iPhone

With the app open from `make phone`, use Safari's Share → Add to
Home Screen for an app-icon install. Details in
`frontend/PWA_NOTES.md`.

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

**Consistency.** Results are cached per video, so the same video
always gives the same answer. A fresh analysis can differ: in our
measured pair of independent runs of the same video (2026-11-03),
the two runs agreed exactly on 4 of the 8 problems found across
both runs — 1 changed verdict and 3 appeared in only one run.
Every finding shows its evidence frame so you can judge it
yourself.

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
