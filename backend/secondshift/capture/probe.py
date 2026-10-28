"""Video probing with ffprobe (spec section 9.1 step 1).

Why: every capture is validated (duration cap, dimensions, fps) before any
money is spent on frames or models.
Depends on: ffprobe system binary, stdlib.
"""

import json
import subprocess
from dataclasses import dataclass


@dataclass
class ProbeResult:
    """The ffprobe facts a Capture is built from."""

    duration_s: float
    width: int
    height: int
    fps: float
    has_audio: bool


class CaptureTooLong(Exception):
    """Raised when a capture exceeds the configured duration cap."""


def probe_video(path: str, max_minutes: float = 6.0) -> ProbeResult:
    """Probe one video file. Raises CaptureTooLong past the cap.

    Example: probe_video("walkthrough.mp4").duration_s -> 132.4
    """
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", path],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(out.stdout)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    duration = float(data["format"].get("duration", video.get("duration", 0)))
    if duration > max_minutes * 60:
        raise CaptureTooLong(
            f"This video is {duration / 60:.1f} minutes. Please keep it under "
            f"{max_minutes:.0f} minutes and try again."
        )
    num, _, den = str(video.get("avg_frame_rate", "30/1")).partition("/")
    fps = float(num) / float(den or 1) if den else 30.0
    return ProbeResult(
        duration_s=duration,
        width=int(video["width"]),
        height=int(video["height"]),
        fps=fps,
        has_audio=has_audio,
    )
