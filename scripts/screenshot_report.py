"""Capture phone-width screenshots of key pages (Phase 3 deliverable).

Uses Playwright with the locally installed Chromium headless shell.
Usage: python scripts/screenshot_report.py <checkup_id> [base_url]
Writes docs/screenshots/{home,report,fixes}-phone.png at 390x844.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent.parent / "docs" / "screenshots"


def main() -> None:
    """Screenshot home, the report for the given checkup, and its fixes."""
    checkup_id = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5173"
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception:
            # Fall back to any locally cached headless shell (version drift).
            import glob

            shells = sorted(
                glob.glob(
                    str(
                        Path.home()
                        / ".cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell"
                    )
                )
            )
            browser = pw.chromium.launch(executable_path=shells[-1])
        page = browser.new_page(viewport={"width": 390, "height": 844})
        for name, path in (
            ("home", "/"),
            ("report", f"/checkup/{checkup_id}/report"),
            ("fixes", f"/checkup/{checkup_id}/fixes"),
        ):
            page.goto(base + path, wait_until="networkidle")
            page.screenshot(path=str(OUT / f"{name}-phone.png"), full_page=name != "report")
            if name == "report":
                page.screenshot(path=str(OUT / "report-phone.png"), full_page=True)
            print(f"{name}: {OUT / f'{name}-phone.png'}")
        browser.close()


if __name__ == "__main__":
    main()
