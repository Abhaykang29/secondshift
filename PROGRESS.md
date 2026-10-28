# Progress

## Phase 0 - Contracts and skeleton (Oct 28) - AWAITING HUMAN REVIEW
- [x] Repo layout per spec 7.3, Makefile, .env.example, docs stubs
- [x] Domain schemas (spec section 8) with docstrings; enums; config
- [x] Provider interfaces, registry, mock skeleton, record/replay cache, cost guard (+ tests)
- [x] Pack loader + validation; full falls (16 items) and babyproofing (13 items) packs; fire safety pack (6 items, stretch - written early as data only)
- [x] FastAPI app: health + packs + costs live; all other resources stubbed with 501
- [x] Frontend shell: all routes as placeholder pages; typed API client; i18n en/hi
- [x] Prompt templates (all 10 required) with version headers
- [x] Eval skeleton: ablation configs, Appendix B sentences, metrics stub

### Verified (2026-10-28)
`make check` exit 0: ruff clean, ruff format clean, `mypy --strict` clean (51 files), **27 pytest passed**, `tsc --noEmit` clean. `make dev` verified live: backend `/api/health` ok, `/api/packs` returns falls=16 items / babyproofing=13, frontend serves 200 on :5173 and proxies /api. `make smoke-meta` correctly reports no META_API_KEY. Cost estimator sanity: ~$0.19/scan rough estimate at default settings.

### What's mocked
Everything model-facing: mock vision returns no proposals (Phase 2 wires scenarios), mock SAM returns deterministic masks, mock image editor returns a placeholder PNG, mock transcriber returns no segments. Meta adapters raise ProviderUnavailable.

### What's risky
- TODO(API): every Meta endpoint detail is unverified until keys arrive (Phase 7, smoke test first).
- TODO(STAT): babyproofing statistics placeholder - team must source from CPSC/AAP.
- TODO(TEAM): no real footage, labels or consent artefacts yet; eval datasets are empty manifests.
- Frontend eslint is not yet in `make check` (tsc is); add eslint config before Phase 3 UI work grows.

### Next
Human review of schemas, packs and skeleton. On approval: Phase 1 (capture) and Phase 2 (scan pipeline on mocks), workers per spec section 16.
