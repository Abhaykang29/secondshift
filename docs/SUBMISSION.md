# Hackathon submission — SecondShift

**Name:** SecondShift

**Tagline:** A safety check for the places people live and work.

**What it is.** An installable phone app (PWA) on a reusable checking
engine. Film a 2–3 minute walkthrough of a home or workplace, pick a
checklist — or type your own in plain English — and get back the
hazards with photographic proof (the evidence frame and the SAM box
that found them), plain-language fixes, honest "can't tell" answers
for anything a camera can't settle, and a re-check that confirms the
fix actually happened. A Live Check mode compiles plain-English
rules ("tell me if the front door opens at night") into watch rules
that answer MET / NOT MET / CANNOT TELL — and refuses the ones no
camera can keep ("warn me before Mom falls"), with alternatives.

**Built with Meta AI:** Muse Spark 1.3 (hazard proposals, evidence
judging, rule compiler, checklist compiler — all via files prompts,
temperature 0, low reasoning effort), SAM 3.1 (verification boxes,
an items-first sweep that catches what proposals miss, person
blurring for privacy, live frame analysis), Muse Image (watermarked
"after" visualizations, composite-feathered into the real photo),
Muse Wonder (routine summaries in the scripted demo). Every model
call is costed in a SQLite ledger behind a hard budget cap; the
whole pass-3 build spent about $5.70 of its $50 live cap.

**Measured, not claimed** (one real, unstaged home walkthrough,
labeled by its owner — `docs/LIVE_VERIFICATION.md` has every run):
the scan reports 7 of the 8 hazards the owner listed, with no false
alarms among reported findings on the acceptance run; ~78 seconds
warm / ~6 minutes cold per scan; about a dollar of model calls per
scan. An ablation (sweep on/off, thin-object crops on/off) is in the
log with an uncomfortable result stated plainly: on this one video
the sweep's extra recall did not repeat — run-to-run variance is the
same size as its contribution, and the thin white cable it was built
for still defeats SAM. We'd rather show that than hide it.

**Ten checklists, one engine:** older adults (falls), babyproofing,
home safety inspection, workplace safety, pets, fire safety, car
seat check, earthquake ready, home from hospital, mosquito breeding
— plus any checklist a user types. The engine (`secondshift.core` +
the `/v1` REST API) is domain-agnostic; the roadmap is workplace
daily walks, trucking walk-arounds, rental condition proof, disaster
triage, and an independent chore-check for robots.

**Honest limits** (also stated in the app on every screen): a
screening tool, not a medical device or an emergency alarm; it can
miss things; it cannot test tightness (the car seat card says so and
gives the 1-inch shake test instead of a verdict), alarms, or
anything out of sight. Voice is not connected — the transcription
endpoint was never located — and the routine step is hidden until a
real routine clip exists to verify it against.

**Try it:** `make demo` (offline scripted demo), `make demo-check`
(passes 3×), `make dev` for the full app. Screenshots:
`docs/screenshots/app/`.
