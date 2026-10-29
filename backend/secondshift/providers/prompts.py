"""Prompt loading (pass 2 Phase B): every live model call reads its
template from backend/secondshift/prompts/*.md via load_prompt().

Why: prompt text in Python strings can't be reviewed, versioned, or
diffed by the team. Templates are Jinja2; the leading
`<!-- prompt: ... -->` header comment is stripped before rendering.
Depends on: jinja2.
"""

from pathlib import Path

from jinja2 import Environment, StrictUndefined

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_env = Environment(undefined=StrictUndefined, autoescape=False)


def load_prompt(name: str, **variables: object) -> str:
    """Render prompts/<name>.md with the given variables."""
    raw = (PROMPTS_DIR / f"{name}.md").read_text()
    if raw.startswith("<!--"):
        raw = raw.split("-->", 1)[1]
    return _env.from_string(raw.strip()).render(**variables)


def prompt_names() -> list[str]:
    """All prompt template names on disk."""
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.md") if p.stem != "README")
