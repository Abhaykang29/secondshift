"""Smoke test for the real Meta API (Phase 7).

Run FIRST when keys arrive: one tiny call per capability (text, one image,
one SAM call, one image edit, one 5-second audio clip). Prints raw response
shapes, latencies and usage fields. TODO(API): everything here is a stub
until endpoints are verified - see docs/API_INTEGRATION.md.
"""

import os


def main() -> None:
    """Report configuration status; real calls land in Phase 7."""
    if not os.environ.get("META_API_KEY"):
        print("META_API_KEY is not set - nothing to smoke-test yet.")
        return
    print("TODO(API): smoke calls land in Phase 7 after endpoint verification.")


if __name__ == "__main__":
    main()
