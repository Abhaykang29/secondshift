"""Generate the synthetic test video (spec section 11.2).

A 60s OpenCV video, 6 scenes x 10s: ENTRY (clutter), HALLWAY (RUG +
DRESSER), LIVING (CORD), STAIRS (objects on stairs), KITCHEN (high shelf),
BATHROOM (TOILET). A PERSON blob walks across every scene and, in the
hallway scene, touches the DRESSER - so frame extraction, keyframes,
routine geometry and segmentation prompts all have real pixels to work on.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

W, H, FPS, SECONDS = 640, 360, 10, 60

SCENES = [
    ("ENTRY", (90, 90, 60)),
    ("HALLWAY", (70, 80, 90)),
    ("LIVING", (80, 70, 70)),
    ("STAIRS", (60, 60, 80)),
    ("KITCHEN", (85, 75, 55)),
    ("BATHROOM", (65, 85, 85)),
]


def draw_scene(frame: np.ndarray, scene: str, t_in_scene: float) -> np.ndarray:
    """Draw one labelled synthetic scene; the person blob walks left->right."""
    cv2.putText(frame, scene, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    if scene == "ENTRY":
        cv2.rectangle(frame, (60, 260), (200, 330), (40, 40, 200), -1)
        cv2.putText(frame, "SHOES", (70, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    elif scene == "HALLWAY":
        cv2.rectangle(frame, (190, 250), (420, 340), (30, 120, 200), -1)
        cv2.putText(frame, "RUG", (270, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.rectangle(frame, (470, 90), (620, 250), (120, 80, 40), -1)
        cv2.putText(
            frame, "DRESSER", (478, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2
        )
    elif scene == "LIVING":
        cv2.line(frame, (10, 300), (630, 315), (20, 20, 20), 6)
        cv2.putText(frame, "CORD", (280, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    elif scene == "STAIRS":
        for i in range(4):
            y = 180 + i * 40
            cv2.rectangle(frame, (120 + i * 30, y), (520, y + 36), (150, 150, 150), -1)
        cv2.rectangle(frame, (250, 210), (330, 246), (40, 40, 200), -1)
        cv2.putText(
            frame, "SHOES ON STAIRS", (180, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
        )
    elif scene == "KITCHEN":
        cv2.rectangle(frame, (90, 30), (460, 110), (110, 90, 60), -1)
        cv2.putText(
            frame, "HIGH SHELF ITEMS", (100, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
        )
    elif scene == "BATHROOM":
        cv2.rectangle(frame, (260, 160), (380, 300), (230, 230, 230), -1)
        cv2.putText(frame, "TOILET", (272, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
    # Person blob walks across the scene over its 10 seconds.
    x = int(40 + (t_in_scene / 10.0) * 500)
    cv2.rectangle(frame, (x, 170), (x + 46, 300), (240, 240, 60), -1)
    cv2.putText(frame, "PERSON", (x - 6, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    if scene == "HALLWAY" and t_in_scene > 6.0:
        # Arm reaches the dresser: the support-contact moment.
        cv2.line(frame, (x + 46, 200), (478, 180), (240, 240, 60), 8)
    return frame


def generate(out_path: str) -> str:
    """Generate the 60s synthetic video and return its path."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for second in range(SECONDS):
        scene, colour = SCENES[second // 10]
        for frame_idx in range(FPS):
            frame = np.full((H, W, 3), colour, dtype=np.uint8)
            writer.write(draw_scene(frame, scene, (frame_idx / FPS) + (second % 10)))
    writer.release()
    return str(out)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Make the synthetic test video")
    parser.add_argument("--out", default="fixtures/synthetic/synthetic.mp4")
    args = parser.parse_args()
    print(f"Wrote {generate(args.out)}")


if __name__ == "__main__":
    main()
