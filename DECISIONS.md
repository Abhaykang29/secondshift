# Decisions

Numbered decision log (ADR-lite). If Muse Code disagrees with the spec, it follows the spec and records its reasoning here.

## D1 - Phase 0 runtime: Python 3.12, minimal installed deps
Spec says Python 3.11+. The build machine runs Python 3.12.3; code targets 3.11+ (`target-version = py311` in ruff, `python_version = 3.11` in mypy). opencv and matplotlib are optional extras (`dev`/`eval`) so `make check` stays fast; capture/eval phases install them.

## D2 - Record/replay cache storage: files on disk, gitignored
Spec section 7.3 left recordings storage open (gitignored or LFS). Phase 0 choice: `fixtures/recordings/*.json` is gitignored. Recordings can contain home imagery references and may be large; the team can move to LFS in Phase 7 when real recordings exist.

## D3 - Frontend Tailwind via PostCSS (v3-style config)
Tailwind is wired with a plain `tailwind.config.js` + PostCSS rather than a component library, per spec section 7.2 ("No component library unless justified"). No justification exists yet.

## D4 - Contributor-tier model IDs banned outside eval/rules
Enforced as a standing rule from spec section 6: no `*-contributor` ID appears anywhere in app code or config. The only permitted future use is `eval/rules/` synthetic text behind `ALLOW_CONTRIBUTOR_FOR_SYNTHETIC_TEXT=1` (default off, present in config).
