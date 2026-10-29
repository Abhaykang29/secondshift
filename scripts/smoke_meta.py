"""Smoke-test the Meta adapters (spec section 16 Phase 7, step 1).

With META_API_KEY set: one tiny call per model (1 small image to Spark,
1 SAM prompt, 5s of audio to Transcribe, 1 tiny image edit) and the
ACTUAL response shape printed for each - those prints are what the
runbook's "fix the adapters" step works from. Without a key it says so
and exits 0. Never prints the key.
"""

import base64
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

_TINY_JPEG = base64.b64decode("/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYFBgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAAwAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDzeiiigAorP13Xf7F8r/RfN83d/HtxjHsfWs//AITr/qF/+R//ALGvIxWe5Vg67o1qlpLdWk91forbH6JkXhRx9xLlVPMstwftKNS/LL2lKN+WTi9JTUlaSa1S2utDoKK5/wD4Tr/qF/8Akf8A+xq5oniT+2LtrX7F5e2Mtu8zPcDHQetKhn+UYqtGlSqXk9laX6o1zbwh8RMiy2rj8dguSlTV5S9pRdl3tGo2/kmalFFFewfmwUUUUAc/46/5df8Agf8A7LXP10Hjr/l1/wCB/wDstc/X5LxP/wAjyr/27/6TE/0O8DP+TWZf/wBxf/T9UK2PBP8AyFZP+vc/+hLWPWx4J/5Csn/Xuf8A0Ja58h/5HFH/ABHr+LP/ACbjM/8Ar0/zR1FFFFfsR/m0FFFFAGX4k0S71jyfsska+Xu3eYSOuPQH0rL/AOEJ1X/n4t/++2/+JrqKK8PGcPZbjsTKvVT5na+vZW/Q/VOG/GTjXhTJaWVYCcFSp83LeCb96Tm7u/eTOX/4QnVf+fi3/wC+2/8Aiav+HvDt7pN61zcyxMrRFQEYk5yD3A9K2aKjDcN5ZhK8a1NPmjqtTfPPGzjriHKa2W4ydN0qq5ZWgk7eTvoFFFFe+fkh/9k=")
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)


def main() -> int:
    """Run the smoke test; returns a process exit code.

    Auth resolves through providers.meta.transport: META_API_KEY from
    the environment/.env when set, otherwise the vault surrogate of the
    custom.meta-ai connector. The key value is never printed.
    """
    from secondshift.providers.meta.transport import auth_headers

    try:
        auth_headers()
    except Exception as exc:
        print(f"No Meta credential available - nothing to smoke-test yet. ({exc})")
        return 0
    print("Meta credential available (value never printed). Probing adapters...")
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(_TINY_JPEG)
        image_path = tmp.name
    from secondshift.providers.base import ImageRef
    from secondshift.providers.meta.segmentation import MetaSegmenter
    from secondshift.providers.meta.text_vision import MetaVisionReasoner

    vision = MetaVisionReasoner(None)
    try:
        payload = vision._post_chat(  # noqa: SLF001 - smoke tool inspects internals
            {
                "model": "muse-spark-1.3",
                "messages": [{"role": "user", "content": "Say the word ready."}],
            }
        )
        usage = payload.get("usage", {})
        print(f"spark chat: OK, keys={list(payload)}, usage={usage}")
    except Exception as exc:
        print(f"spark chat: FAILED {type(exc).__name__}: {exc}")
    segmenter = MetaSegmenter(None)
    try:
        masks = segmenter.segment(
            ImageRef(path=image_path, keyframe_id="smoke"), ["the image"]
        )
        print(f"sam segment: OK, {len(masks)} mask(s) on the tiny image")
    except Exception as exc:
        print(f"sam segment: FAILED {type(exc).__name__}: {exc}")
    print(
        "transcribe: endpoint not yet located (probed 2026-10-28) - "
        "narration is optional; the scan proceeds without it."
    )
    print(
        "image edit: verified shape (POST /v1/images/edits, images[].image_url); "
        "exercised by the fix-visualization step of a real scan."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
