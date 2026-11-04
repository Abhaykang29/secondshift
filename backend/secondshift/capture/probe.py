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


class CaptureUnreadable(Exception):
    """Raised when a file cannot be probed as a video at all -
    truncated, corrupted, or not a video (robustness sweep 2026-11-03:
    these used to escape as a 500)."""


UNREADABLE_MESSAGE = (
    "We couldn't read that file as a video. It may be damaged or not "
    "a video at all - please upload a video recorded on a phone or "
    "camera (MP4 or MOV) and try again."
)


def probe_video(path: str, max_minutes: float = 6.0) -> ProbeResult:
    """Probe one video file. Raises CaptureTooLong past the cap and
    CaptureUnreadable when the file is not a readable video.

    Example: probe_video("walkthrough.mp4").duration_s -> 132.4
    """
    try:
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
        width = int(video["width"])
        height = int(video["height"])
    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        StopIteration,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise CaptureUnreadable(UNREADABLE_MESSAGE) from exc
    if duration > max_minutes * 60:
        raise CaptureTooLong(
            f"This video is {duration / 60:.1f} minutes. Please keep it under "
            f"{max_minutes:.0f} minutes and try again."
        )
    num, _, den = str(video.get("avg_frame_rate", "30/1")).partition("/")
    fps = float(num) / float(den or 1) if den else 30.0
    return ProbeResult(
        duration_s=duration,
        width=width,
        height=height,
        fps=fps,
        has_audio=has_audio,
    )
