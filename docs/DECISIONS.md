# Decisions

Architecture and implementation decisions, newest first. Earlier
decisions (D1–D10) are recorded in `docs/BUILD_LOG.md`.

## D11 — Transport cache keys exclude fields that cannot change the output (2026-10-30, Pass 3 P1.5)

The Meta transport cache keys on the exact request body. Anything in
a body that varies without changing what the model can answer poisons
the cache: the same home re-filmed produced a different key on every
call, so warm re-checks paid full price.

Excluded, with reasons:

- **Propose image labels: the keyframe id.** `build_propose_payload`
  labeled each image `keyframe_id=<random per capture>; timestamp=…`.
  The model never needs the id (it answers with timestamps and image
  positions); the pipeline maps its answer back to frames itself.
  Labels now carry the image index and timestamp only. The timestamp
  stays: the model's output depends on it.
- Nothing else was excluded. Fields deliberately KEPT in keys:
  - `temperature` and `reasoning_effort` — they change the sampling
    and therefore the output distribution.
  - Prompt text, pack YAML, narration facts — the answer depends on
    them.
  - Hazard ids in judge/fix-plan calls — index-based and stable for
    identical proposals, and the answers reference them.
  - The resident/home label in report summaries — it appears in the
    generated text.

SAM calls needed no change: their bodies carry only the image bytes
and the prompt text.
