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

## D5 - Keyframe change threshold mapping
Spec section 9.2 defines scene-change as 1 - histogram correlation with SCENE_CHANGE_MIN=0.25. Our descriptor is a 32x32 grayscale MAD; the API maps the config value as change_min = SCENE_CHANGE_MIN / 16 (empirically equivalent on synthetic + flat scenes: 59 keyframes at defaults). The pure function takes change_min directly and is unit-tested; the mapping lives in one place (api/captures.py) and must be re-tuned on real footage in Phase 7.

## D6 - Storage: JSON file repository behind the Repository interface
Spec section 7.2 names sqlite3 stdlib with a thin repository layer. Phase 1 ships a JSON-file-backed repository with the identical interface (simpler to inspect during the hackathon; data volumes are tiny). SQLite can replace it behind the interface without caller changes.

## D7 - Demo replay keys are scenario-level
Production cache keys (section 11.3) hash the full request. The Phase 8
demo recording keys responses by (endpoint, scenario) instead, because
the demo must replay deterministically against synthetic keyframes whose
image hashes do not exist as files. The guarantee that matters is kept:
replay mode raises CacheMiss rather than ever calling through. When real
recordings are made in Phase 7 step 5, record them through the same
wrappers - the keying is contained in providers/replay.py.
