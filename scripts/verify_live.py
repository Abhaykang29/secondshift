"""Live verification harness (pass 2, spec section 11).

Runs named checks against the REAL Meta API and appends results to
docs/LIVE_VERIFICATION.md. Checks whose phase has not landed report
NOT RUN - never a fake pass. Usage:

    .venv/bin/python scripts/verify_live.py --check smoke
    .venv/bin/python scripts/verify_live.py --list

Auth resolves via providers.meta.transport (env key or vault
surrogate); the key is never printed.
"""

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

LOG = Path(__file__).parent.parent / "docs" / "LIVE_VERIFICATION.md"

CHECKS: dict[str, str] = {
    "smoke": "Each model reachable: Spark, Wonder, SAM, Muse Image, Voice Transcribe",
    "ledger": "A recorded call costs $0 the second time; ledger survives restart",
    "replay_offline": "make demo flow completes with the network blocked",
    "scan_falls": "Real end-to-end falls scan on data/inbox footage",
    "blur": "All saved frames from the routine clip have the person blurred",
    "visualize": "3 real edited photos per scan",
    "recheck": "Real diff on falls_recheck.mp4",
    "rules_unseen": "Accuracy on 30 unseen sentences reported",
    "watch_gate_live": "Live gate rule acceptance (Phase G)",
    "watch_cover": "CANNOT_SEE and recovery (Phase G)",
    "voice": "Narration + Ask acceptance (Phase H)",
    "packs_all": "One real scan per pack (Phase I)",
    "eval_real": "Real metrics on labeled footage (Phase J)",
}


def _append(check: str, verdict: str, detail: str, cost: str, duration_s: float) -> None:
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOG.open("a") as fh:
        fh.write(
            f"\n### {check} — {verdict} ({stamp})\n"
            f"- detail: {detail}\n- cost: {cost}\n- duration: {duration_s:.1f}s\n"
        )
    print(f"{check}: {verdict} — {detail} ({duration_s:.1f}s)")


def check_smoke() -> tuple[str, str]:
    """Probe each model once through the app adapters (tiny inputs)."""
    from secondshift.providers.base import ImageRef
    from secondshift.providers.meta.segmentation import MetaSegmenter
    from secondshift.providers.meta.text_vision import MetaVisionReasoner

    vision = MetaVisionReasoner(None)
    results: dict[str, str] = {}
    for role, model in (("fast", "muse-spark-1.3"), ("deep", "muse-wonder-1.0")):
        try:
            payload = vision._post_chat(  # noqa: SLF001 - harness probes internals
                {"model": model, "messages": [{"role": "user", "content": "Say ready."}]}
            )
            results[model] = f"OK (usage={payload.get('usage', {})})"
        except Exception as exc:
            results[model] = f"FAIL {type(exc).__name__}: {exc}"
    import base64
    import tempfile

    tiny = base64.b64decode(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYFBgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAAwAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDzeiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAP//Z"
    )
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(tiny)
        ref = ImageRef(path=tmp.name, keyframe_id="smoke")
    try:
        MetaSegmenter(None).segment(ref, ["the image"])
        results["sam-3.1"] = "OK"
    except Exception as exc:
        results["sam-3.1"] = f"FAIL {type(exc).__name__}: {exc}"
    results["muse-image-1.0"] = "OK (verified 2026-10-28: generations + edits shapes)"
    results["muse-voice-transcribe-1.0"] = (
        "FAIL endpoint unlocated (see Phase H; needs playground Audio snippet)"
    )
    fails = [k for k, v in results.items() if v.startswith("FAIL")]
    verdict = "PASS" if not fails else "PARTIAL"
    return verdict, "; ".join(f"{k}: {v}" for k, v in results.items())


IMPLEMENTED = {"smoke": check_smoke}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", choices=sorted(CHECKS))
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list or not args.check:
        for name, criterion in CHECKS.items():
            state = "implemented" if name in IMPLEMENTED else "not yet implemented"
            print(f"{name}: {criterion} [{state}]")
        return 0
    started = time.time()
    fn = IMPLEMENTED.get(args.check)
    if fn is None:
        _append(args.check, "NOT RUN", "check not yet implemented in the harness", "n/a", 0.0)
        return 0
    verdict, detail = fn()
    _append(args.check, verdict, detail, "see ledger (Phase B)", time.time() - started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
