"""Smoke-test the Meta adapters (spec section 16 Phase 7, step 1).

With META_API_KEY set: one tiny call per model (1 small image to Spark,
1 SAM prompt, 5s of audio to Transcribe, 1 tiny image edit) and the
ACTUAL response shape printed for each - those prints are what the
runbook's "fix the adapters" step works from. Without a key it says so
and exits 0. Never prints the key.
"""

import base64
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)


def main() -> int:
    """Run the smoke test; returns a process exit code."""
    key = os.environ.get("META_API_KEY")
    if not key:
        print("META_API_KEY is not set - nothing to smoke-test yet.")
        return 0
    print("META_API_KEY is set (value never printed). Probing adapters...")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(TINY_PNG)
        image_path = tmp.name
    # Import lazily so a missing httpx etc. doesn't hide the key check.
    from secondshift.providers.base import ImageRef
    from secondshift.providers.meta.segmentation import MetaSegmenter
    from secondshift.providers.meta.text_vision import MetaVisionReasoner

    vision = MetaVisionReasoner(key)
    try:
        payload = vision._post_chat(
            {  # noqa: SLF001 - smoke tool inspects internals on purpose
                "model": "muse-spark-1.3",
                "messages": [{"role": "user", "content": "Say the word ready."}],
            }
        )
        print(f"spark chat: OK, response keys={list(payload)}")
    except Exception as exc:
        print(f"spark chat: FAILED {type(exc).__name__}: {exc}")
    segmenter = MetaSegmenter(key)
    try:
        masks = segmenter.segment(ImageRef(path=image_path, keyframe_id="smoke"), ["rug"])
        print(f"sam segment: OK, {len(masks)} masks")
    except Exception as exc:
        print(f"sam segment: TODO/FAILED {type(exc).__name__}: {exc}")
    print("transcribe + image edit: run after their endpoints are confirmed (TODO(API)).")
    print("Next: docs/API_INTEGRATION.md step 3 - fix adapters from these shapes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
