"""Frame and audio extraction with ffmpeg (spec section 9.1 steps 2, 4).

Frames are extracted at SAMPLE_FPS to data/<checkup>/<capture>/frames/;
the audio track (if any) becomes narration.wav for the Transcriber.
Depends on: ffmpeg system binary, stdlib.
"""

import subprocess
from pathlib import Path


def extract_frames(video_path: str, out_dir: str, sample_fps: float) -> list[Path]:
    """Extract frames at sample_fps as JPEGs; return their paths in order."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            video_path,
            "-vf",
            f"fps={sample_fps}",
            "-q:v",
            "3",
            str(out / "frame_%05d.jpg"),
        ],
        check=True,
    )
    return sorted(out.glob("frame_*.jpg"))


def extract_audio(video_path: str, out_path: str) -> Path | None:
    """Extract the audio track to a 16kHz mono WAV, or None if silent."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            out_path,
        ],
        capture_output=True,
    )
    path = Path(out_path)
    if result.returncode != 0 or not path.exists() or path.stat().st_size < 1000:
        return None
    return path
