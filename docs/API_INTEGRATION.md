# Meta API integration - Phase 7 checklist

ALL of this is TODO(API) until verified against https://dev.meta.ai docs and `make smoke-meta`.

- [ ] Base URL `https://api.meta.ai/v1`, auth `Authorization: Bearer $META_API_KEY`, OpenAI-compatible.
- [ ] Text/vision: `POST /v1/chat/completions` (also `/v1/responses`; Anthropic-style `/v1/messages` reportedly exists). Verify image content-part format (base64 data URL vs URL) and size limits; verify video part format for Muse Spark.
- [ ] Structured output via `response_format` JSON schema - verify.
- [ ] Muse Image: `/v1/images/generations` and `/v1/images/edits` - verify multipart fields (image + mask + prompt) and mask convention (transparent = edit?).
- [ ] Voice: `POST /v1/asr/transcribe` (file) and realtime `wss://api.meta.ai/v1/asr/realtime`. Language bias for code-switching. Validated languages include English, Hindi, Bengali, Kannada, Marathi, Tamil, Telugu; **Punjabi is not in the validated list - test before promising it.**
- [ ] SAM 3.1: model id `sam-3.1`; endpoint path and request/response format UNKNOWN - normalize polygon/RLE/PNG into our Mask. If video tracking is not exposed, use per-frame calls.
- [ ] Rate limits are per team (Spark ~3,000 RPM; Muse Image ~150 RPM): client-side throttling, exponential backoff with jitter on 429/5xx, max 3 retries.
- [ ] Run `scripts/smoke_meta.py` FIRST when keys arrive; print raw response shapes, latencies, usage fields; then update adapters + this doc.
- [ ] Measure real image token counts; update `IMAGE_TOKENS_ESTIMATE` in config + DECISIONS.md.
- [ ] Standard tier only for real media. Never a `*-contributor` ID in the app.
- [ ] Never log API keys, RTSP credentials, raw images or audio.
