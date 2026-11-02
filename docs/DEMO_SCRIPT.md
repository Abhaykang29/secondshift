# Demo script (3:00) — Pass 3

Positioning line (say it once, early): **"SecondShift — a safety check
for the places people live and work. Film a walkthrough, get the
hazards with proof, honest 'can't tell' answers, and a re-check that
confirms the fix."**

All footage is real team footage. Every number below is a measured
number from `docs/LIVE_VERIFICATION.md` — update them from the log
the night before filming, never from memory.

| Time | Shot | Notes |
|---|---|---|
| 0:00–0:20 | **The problem.** An older parent's home, morning light. Fact cards: 1 in 4 adults over 65 fall each year (CDC); home hazard fixes cut falls by about 26% (Cochrane 2023). | Sourced facts only — the two cards in `docs/IMPACT.md`. No stock footage of people falling. |
| 0:20–1:10 | **The hero check.** Film the walkthrough (Ray-Ban Meta: "Hey Meta, take a video", import from Photos) → the app: pick "Older adults — falls" → consent → capture guide → processing with live steps → report. Land on: SAM-boxed hazards ("Found by SAM (box)"), the absence logic catch (no extinguisher → **needs a human look**, not a fake pass), the **couldn't-check** list said out loud, a clean after-photo slider, then the real fix on camera (move the plant / reroute the cord) and **re-check: Resolved ✓, score before → after**. | This is the whole product in 55 seconds. The after-photo must be one of the clean ones (removal / lamp) — never the miniature-inset failure mode. |
| 1:10–1:30 | **Guided re-film.** The report's "I couldn't see these" card: "It couldn't see the bathroom wall, so it tells you where to look" - the instruction for the grab bar, filmed as a 20-second follow-up clip (stored results on camera, never a live cold scan) → back in the report, the item flips from **Can't tell** to its answer, labelled "From follow-up clip". | This is the honesty feature working, not just talking: can't-tell is a filming task, not a dead end. Film this beat with a REAL follow-up clip during the Nov 3-4 shoot (the demo home has a bathroom; test_1 doesn't, so its three verification cuts honestly stayed can't-tell - see LIVE_VERIFICATION.md). The stored test_1 report shows the card + instructions on camera. |
| 1:30–1:45 | **The honesty moment.** Live Check: type "Warn me before Mom falls." → the app **refuses**, explains why, offers alternatives. Pick one ("tell me if the front door opens at night") → it compiles into a rule card with spot, timing and who gets told. | This beat is the trust story. Don't rush it. |
| 1:45–2:05 | **Second use case, same engine.** A workplace walk: space heater next to cardboard, cords across a walkway (workplace pack) → findings → one fix → re-check ✓. | BLS 2024 card if a fact is needed (see IMPACT.md). No new code on screen — same flow, different checklist. |
| 2:05–2:20 | **Montage (5s each).** Babyproofing finding · car seat card showing the 1-inch shake-test line ("I can't check how tight it is…") · pet finding · Live Check alert firing on the gate + a covered lens answering "Can't see". | The car-seat line is the honesty thesis in one sentence — hold it a beat longer. |
| 2:20–2:40 | **Proof.** The numbers card: on a real, unstaged home walkthrough the scan found 7 of the 8 hazards the owner listed, with no false alarms among the reported findings; a typical scan takes ~2 minutes warm / ~6 minutes cold and costs about a dollar in model calls. Then **one honest failure** on screen: the thin white cable on light flooring that SAM could not see, reported only under the pet pack's name. | Numbers from the P1 acceptance + P6 ablation entries in LIVE_VERIFICATION.md. The failure is a feature of this section, not an apology. |
| 2:40–3:00 | **The engine layer.** In the app: Custom check → type three lines live ("trailer doors closed and sealed", "fire extinguisher mounted by the exit", "no boxes stacked above shoulder height") → they compile into checks (one refusal if a line needs hands, not a camera) → run. Close on the roadmap line: "The same layer that checks a home can check a warehouse, a truck walk-around — an independent check for robots. SecondShift is the first app on it." | Custom compile is live Spark — rehearse the exact lines; they are verified in the P4 log entry. |

## Tech fallbacks (rehearse these)

- **No network on stage:** `make demo` serves the app in demo
  configuration and `make demo-check` passes 3× offline — the
  scripted demo (recorded scenario) replays from its cache, and the
  app's demo-home flow works with no provider calls.
- **Real-footage fallback:** the recorded real scans' reports are in
  the app's store and open with **no provider calls at all** — open
  one from the Homes tab. (`make demo-reset` removes the build's
  test places before recording; results stay in LIVE_VERIFICATION.md.)
- **Do not** promise a fresh live re-scan as an instant fallback:
  replaying a real scan through a new upload is not bit-exact
  (person-blur output varies slightly between runs, which changes
  image hashes). A fresh live scan works, it just takes ~2–6
  minutes — say so if asked.
- Voice is **not** in this build (the transcription endpoint was
  never located and no team audio sample arrived) — do not mention
  voice features on stage; narration is not transcribed.
- The routine step is hidden in the app: the live routine feeder is
  not built and no team routine clip exists to verify it against.
  The scripted demo's routine insight (support contacts) is recorded
  and replays in `make demo-check`.
