"""make demo - the FULL app on http://localhost:8000, no key needed.

- builds the frontend when frontend/dist is missing,
- seeds the recorded real results (scripts/seed_demo.py) so the
  Homes tab shows real reports immediately,
- serves the frontend from the backend (SERVE_FRONTEND=1) together
  with the API on one origin.

The provider defaults to mock for anything new a visitor scans;
recorded reports are labeled "Recorded real result" in the UI and
never show the mock banner. Set PROVIDER=meta with a key in the
environment to demo live scans instead.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _frontend_is_stale(dist: Path) -> bool:
    """True when any frontend source file is newer than the built app,
    so a `git pull` never serves an old UI."""
    index = dist / "index.html"
    if not index.exists():
        return True
    built = index.stat().st_mtime
    front = ROOT / "frontend"
    sources = [*(front / "src").rglob("*"), front / "index.html", front / "tailwind.config.js",
               front / "package.json"]
    return any(p.is_file() and p.stat().st_mtime > built for p in sources)


def _key_present() -> bool:
    """META_API_KEY from the real environment or the gitignored .env.
    The value is never printed."""
    if os.environ.get("META_API_KEY", "").strip():
        return True
    env_file = ROOT / ".env"
    if not env_file.exists():
        return False
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "META_API_KEY" and value.strip().strip("\"'"):
            return True
    return False


def main() -> int:
    live = "--live" in sys.argv[1:]
    if live and not _key_present():
        print("live: no META_API_KEY found, so live scans can't run.")
        print("  1. cp .env.example .env        (if you have no .env yet)")
        print("  2. open .env and set META_API_KEY=<your Meta Model API key>")
        print("  3. make live")
        print("No key? `make demo` shows the recorded real results without one.")
        return 2

    dist = ROOT / "frontend" / "dist"
    if not dist.exists() or _frontend_is_stale(dist):
        npm = shutil.which("npm")
        if npm is None:
            print("demo: the frontend build is missing or out of date and npm was not found.")
            print("Install Node.js 20+, then run: cd frontend && npm install && npm run build")
            return 1
        print("demo: building the frontend (missing or older than the source)...")
        subprocess.run([npm, "install"], cwd=ROOT / "frontend", check=True)
        subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", check=True)

    seed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_demo.py")],
        cwd=ROOT,
    )
    if seed.returncode != 0:
        return seed.returncode

    env = dict(os.environ)
    if live:
        env["PROVIDER"] = "meta"
        print("live: Meta models on - new videos are analysed for real (about 3-7 min per 1-min video,", flush=True)
        print("      roughly $1 of API credit per 1-minute video). Frames go to Meta's API.", flush=True)
    else:
        env.setdefault("PROVIDER", "mock")
    env["SERVE_FRONTEND"] = "1"
    print("Open http://localhost:8000", flush=True)
    proc = subprocess.run(
        [
            sys.executable, "-m", "uvicorn", "secondshift.main:app",
            "--app-dir", str(ROOT / "backend"), "--port", "8000",
        ],
        cwd=ROOT,
        env=env,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
