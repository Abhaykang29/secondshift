#!/usr/bin/env python3
"""make doctor - plain-language environment checks with exact fixes.

Every check prints PASS, WARN (works anyway) or FAIL with the exact
command that fixes it. Never a stack trace: any unexpected error is
reported as a FAIL line with what to try.
"""

import os
import shutil
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILURES = 0
WARNINGS = 0


def ok(name: str, detail: str = "") -> None:
    print(f"  PASS  {name}{(' - ' + detail) if detail else ''}")


def warn(name: str, problem: str, fix: str) -> None:
    global WARNINGS
    WARNINGS += 1
    print(f"  WARN  {name} - {problem}")
    print(f"        Fix: {fix}")


def fail(name: str, problem: str, fix: str) -> None:
    global FAILURES
    FAILURES += 1
    print(f"  FAIL  {name} - {problem}")
    print(f"        Fix: {fix}")


def check_python() -> None:
    v = sys.version_info
    if (v.major, v.minor) >= (3, 12):
        ok("Python", f"{v.major}.{v.minor}.{v.micro}")
    else:
        fail(
            "Python",
            f"found {v.major}.{v.minor}, need 3.12+",
            "install Python 3.12 (Ubuntu: sudo apt install python3.12 python3.12-venv; "
            "macOS: brew install python@3.12), then run: make setup",
        )


def check_venv() -> None:
    py = ROOT / ".venv" / "bin" / "python"
    if not py.exists():
        fail("Backend environment", ".venv not created yet", "run: make setup")
        return
    import subprocess

    probe = subprocess.run(
        [str(py), "-c", "import fastapi, pydantic, cv2"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        ok("Backend environment", ".venv with dependencies")
    else:
        fail(
            "Backend environment",
            ".venv exists but dependencies are missing/broken",
            "run: make setup",
        )


def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        ok("ffmpeg", "video decoding available")
    else:
        fail(
            "ffmpeg",
            "ffmpeg/ffprobe not on PATH (uploads cannot be read without it)",
            "Ubuntu: sudo apt install ffmpeg  |  macOS: brew install ffmpeg",
        )


def check_node() -> None:
    node = shutil.which("node")
    if not node:
        fail(
            "Node.js",
            "not on PATH (the web UI cannot build without it)",
            "install Node 20 LTS from https://nodejs.org, then run: make setup",
        )
        return
    import subprocess

    out = subprocess.run([node, "--version"], capture_output=True, text=True)
    version = out.stdout.strip().lstrip("v")
    try:
        major = int(version.split(".")[0])
    except ValueError:
        major = 0
    if major >= 18:
        ok("Node.js", f"v{version}")
    else:
        fail("Node.js", f"found v{version}, need 18+", "install Node 20 LTS from https://nodejs.org")


def check_ports() -> None:
    for port, name in ((8000, "backend"), (5173, "frontend")):
        sock = socket.socket()
        sock.settimeout(0.3)
        try:
            sock.bind(("127.0.0.1", port))
            ok(f"Port {port}", f"{name} port is free")
        except OSError:
            warn(
                f"Port {port}",
                f"something is already using the {name} port (a dev server may already be running)",
                f"to free it: fuser -k {port}/tcp",
            )
        finally:
            sock.close()


def check_key() -> None:
    if os.environ.get("META_API_KEY"):
        ok("Meta API key", "META_API_KEY is set - live scans available")
        return
    env_file = ROOT / ".env"
    if env_file.exists() and "META_API_KEY" in env_file.read_text(errors="ignore"):
        ok("Meta API key", "found in .env - live scans available")
        return
    warn(
        "Meta API key",
        "not set - live scans are off, but the demo works without one",
        "for live scans: cp .env.example .env and set META_API_KEY in it",
    )


def check_disk() -> None:
    free_gb = shutil.disk_usage(ROOT).free / 1e9
    if free_gb >= 2:
        ok("Disk space", f"{free_gb:.0f} GB free")
    else:
        fail(
            "Disk space",
            f"only {free_gb:.1f} GB free (scans store frames + reports)",
            "free at least 2 GB, or move the clone to a bigger disk",
        )


def main() -> int:
    print("SecondShift doctor - checking this machine:\n")
    for check in (
        check_python,
        check_venv,
        check_ffmpeg,
        check_node,
        check_ports,
        check_key,
        check_disk,
    ):
        try:
            check()
        except Exception as exc:  # never a stack trace
            fail(check.__name__, f"check itself failed ({type(exc).__name__})", "re-run: make setup, then make doctor again")
    print()
    if FAILURES:
        print(f"{FAILURES} problem(s) to fix above, {WARNINGS} warning(s). Then run: make doctor")
        return 1
    if WARNINGS:
        print(f"No blockers. {WARNINGS} warning(s) above - the demo still runs. Try: make demo")
        return 0
    print("All good. Try: make demo  (or PROVIDER=meta make dev for live scans)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
