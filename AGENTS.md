# AGENTS.md: set up and run SecondShift for a person

You are a coding agent (Claude Code, Muse Code, Codex, Cursor, or similar) and
someone has asked you to "set this up" or "let me try it". Follow these steps
in order. Keep your messages short and plain; the person may not be a developer.

SecondShift turns plain-English rules into checks a camera can run. You give it a
video (or a live camera), and every item comes back **Yes / No / Can't tell**
with the frame that proves it.

## 1. Check the machine

```bash
make doctor
```

Every problem it prints comes with the exact fix. Apply the fixes, then run it
again until it says **No blockers**. A warning about `META_API_KEY` is expected
at this point.

- Needs Python 3.12+, Node.js 20+, ffmpeg, and about 2 GB of free disk.
- **Windows:** use WSL (Ubuntu) and run everything inside it. `make` and the
  scripts assume a Unix shell.
- ffmpeg missing: macOS `brew install ffmpeg`; Ubuntu/WSL
  `sudo apt-get install -y ffmpeg`.

## 2. Install

```bash
make setup
```

This creates `.venv/` and installs the frontend packages (about 1–2 minutes).

## 3. Show it working with no key (always do this first)

```bash
make demo
```

Then tell the person: **"Open http://localhost:8000"**. They'll see recorded real
results from Meta's models (marked "Recorded real result"): evidence frames,
SAM boxes, and the honest "can't tell" items. Nothing is sent anywhere in this mode.
Stop it with Ctrl+C before step 5.

## 4. Ask for the API key (only if they want to try their own videos)

Ask the person for their **Meta Model API key** (from the Meta developer
dashboard). Then:

```bash
cp -n .env.example .env
```

and set the line `META_API_KEY=<their key>` in `.env`.

**Key rules (MUST):** write the key only into `.env`, which is gitignored. Never
print it, echo it back, put it in a command line, log it, or commit it. Don't
change any other line in `.env` unless the person asks.

Tell them before they start: **videos are analysed by Meta's API** (people are
blurred in every frame first), a 1-minute video takes **about 3–7 minutes** and
uses roughly **$1** of API credit.

## 5. Run it for real

```bash
make live
```

Then tell the person: **"Open http://localhost:8000"** and walk them through one of these:

**A. Check a video (pre-recorded or new)**
1. **Check** tab → pick up to 3 checklists (e.g. *Parent's home (falls)*,
   *Fire safety*, *Workplace safety*), or write your own with *Your own checklist*.
2. **Start the check**, then either **upload a video file** (.mp4 or .mov,
   up to 6 minutes; 30–90 seconds works best) or **record one with the camera**.
3. Wait on the progress screen (about 3–7 minutes for a 1-minute video). The report shows each finding with
   its evidence frame, what it couldn't check and why, and what to film again.
4. Optional: fix something, film again, and use **Re-check** to see Fixed /
   Still there.

Good test video: walk slowly through a room, phone held sideways, lights on,
pause 2 seconds on floors, shelves, outlets and the stove. No faces, papers or
screens. If `fixtures/sample_videos/` exists, any clip there works too.

**B. Live Check (a camera watching one spot)**
1. **Live** tab → type a rule in plain English, e.g.
   *"Tell me if the door is open for more than 30 seconds."* (Use *Test a rule
   sentence* to see how a rule compiles first.)
2. It either compiles the rule into a check or refuses honestly and says why
   (e.g. it can prove a stove is **on** but won't promise it's **off**).
   Bathrooms are always refused; bedrooms need the resident's consent.
3. Start watching, then tap **Open the phone camera** on the device that will
   film (a second browser tab on the same laptop works) and point it at the spot.
   Status streams in as **watching / pending / ALERT / can't see**. No video is saved.

Live Check answers **rules**. It doesn't list every hazard in the room. For a full
hazard list, use **A** with a short walkthrough.

**On a phone:** stop the server and run `make phone` instead. It prints a URL
and QR code for the same Wi-Fi (`make phone TUNNEL=1` if the office Wi-Fi blocks
devices from seeing each other). Accept the certificate warning once in Safari.

## 6. If something goes wrong

| Symptom | Fix |
|---|---|
| Page says "Not Found" or looks old | Ctrl+C, then `make demo` / `make live` again (it rebuilds the app when the code changed). |
| `make live` says no key | Step 4. |
| Port 8000 in use | Stop the other server (Ctrl+C), or `lsof -i :8000` and stop that process. |
| "We couldn't read that file as a video" | Use .mp4 or .mov; re-export from Photos if needed. |
| Rate limit / 429 from Meta | Wait a minute and retry. The app already retries 3 times. |
| Budget message | The spend guard (`BUDGET_USD` in `.env`) was reached. Raise it only if the person agrees. |
| Anything else | `make doctor`, then read `docs/ROBUSTNESS.md` and `docs/LIVE_VERIFICATION.md`. |

## 7. What not to do

- Don't edit code to "make it work" without telling the person what you changed.
- Don't commit or push anything, and never commit `.env`, `data/` or videos.
- Don't claim results the app didn't show. Report exactly what the report says,
  including "can't tell".

## For developers

`make check` (tests, types, lint) and `make demo-check` (offline demo proof)
need no key. Architecture: `ARCHITECTURE.md`. Measured accuracy and its limits:
`eval/HONESTY.md`.
