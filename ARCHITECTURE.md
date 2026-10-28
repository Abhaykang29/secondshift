# Architecture

## Diagram

See spec section 7.1: a mobile-first React+TypeScript frontend talks to a FastAPI backend over REST + SSE + WebSocket (`/api/...`). The backend is layered: `api/` (thin routes) -> `jobs/` -> `capture/`, `pipeline/`, `recheck/`, `rules/`, `watch/`, `privacy/` -> `providers/` (mock/meta/local, cache, cost guard) and `storage/`. An offline `eval/` harness sits beside it.

## Data flow: one check-up, upload to report

1. Frontend creates a Checkup (consent first) and uploads a walkthrough Capture.
2. `capture/` runs ffprobe/ffmpeg, scores frame quality, selects keyframes, extracts audio.
3. Narration is transcribed and routine facts are extracted (health details dropped).
4. `pipeline/propose.py` asks the VisionReasoner for HazardProposals against the loaded packs, in batches.
5. `pipeline/verify.py` asks SAM to segment each proposal: SAM is the verifier. Presence and absence logic produce a Verification per hazard.
6. `pipeline/routine.py` computes support contacts and path obstacles from the routine clip.
7. `pipeline/rank.py` dedupes and computes the deterministic risk score; top 5 become "Fix these first".
8. `pipeline/fixes.py` picks fixes from the pack library only; `pipeline/visualize.py` renders watermarked "after" pictures for the top 3.
9. `reports/` assembles the Report JSON + printable HTML; the React report page renders the same JSON.

## Glossary

- **Anchor** - the object that must be visible to judge an absence hazard (e.g. the toilet, for a missing grab bar).
- **Safety object** - the missing thing an absence hazard is about (e.g. the grab bar).
- **Keyframe** - a selected still frame from a capture, with quality metrics.
- **ROI** - region of interest in Watch mode; only this region is ever analyzed or sent to a model.
- **Primitive** - one of the small set of checkable rule conditions (spec section 8).
- **Outcome** - a rule's three-state answer: MET / NOT_MET / CANNOT_TELL.
- **Confirmation** - in Watch, repeated true checks (plus any duration) before an ALERT fires.

## Where do I change X?

| Change | Place |
|---|---|
| A threshold or price | `backend/secondshift/config.py` (only there) |
| A checklist / use case | Add one YAML file in `backend/secondshift/checklists/packs/` - no code change |
| A prompt | `backend/secondshift/prompts/*.md` (only there) |
| Meta API HTTP details | `backend/secondshift/providers/meta/` (only there) |
| A domain field | `backend/secondshift/domain/` + `frontend/src/api/types.ts` + drift test + DECISIONS.md |
| Risk-score formula | `backend/secondshift/pipeline/rank.py` (Phase 2) |
