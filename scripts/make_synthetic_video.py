"""Generate the synthetic test video (Phase 1 completes this).

Spec section 11.2: a 60s OpenCV video with coloured rectangles labelled
RUG, CORD, TOILET and a moving PERSON blob that touches a DRESSER, so frame
extraction, keyframes, routine geometry and the watch state machine can be
tested end to end on real pixels. Phase 0: placeholder entry point.
"""

import argparse


def main() -> None:
    """Parse args; generation lands in Phase 1."""
    parser = argparse.ArgumentParser(description="Make the synthetic test video")
    parser.add_argument("--out", default="fixtures/synthetic/synthetic.mp4")
    args = parser.parse_args()
    print(f"Synthetic video generation lands in Phase 1 (target: {args.out}).")


if __name__ == "__main__":
    main()
