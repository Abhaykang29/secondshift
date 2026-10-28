"""Report rendering and sharing (spec section 9.10).

HTML via Jinja2 with print CSS; share text for WhatsApp via the Web Share
API / wa.me link - no WhatsApp Business API.
Depends on: jinja2, domain.hazards.
"""

from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

from secondshift.domain.hazards import Report

_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")))


def render_html(report: Report, language: str = "en") -> str:
    """Render the printable HTML report."""
    titles = {h.id: h.title for h in report.hazards}
    template = _env.get_template("report.html.j2")
    return template.render(
        report_language=language,
        checkup_id=report.checkup_id,
        summary=report.summary,
        fix_first_titles=[titles.get(hid, hid) for hid in report.fix_first],
        hazards=[h.model_dump() for h in report.hazards],
        cannot_assess=[c.model_dump() for c in report.cannot_assess],
        disclaimer=report.disclaimer,
    )


def share_text(report: Report, resident_label: str | None) -> str:
    """The prepared WhatsApp share text for a report."""
    titles = {h.id: h.title for h in report.hazards}
    name = resident_label or "Home"
    top = [titles.get(hid, hid) for hid in report.fix_first[:3]]
    confirmed = len(report.fix_first)
    return (
        f"{name}'s home check-up: {len(report.hazards)} things found, "
        f"top {min(confirmed, 3)} to fix first: {', '.join(top)}. "
        "Full report attached."
    )


def whatsapp_link(report: Report, resident_label: str | None) -> str:
    """A wa.me share link carrying the prepared text."""
    return f"https://wa.me/?text={quote(share_text(report, resident_label))}"
