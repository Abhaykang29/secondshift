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


def main() -> int:
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
