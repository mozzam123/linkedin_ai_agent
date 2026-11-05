from functools import lru_cache
from pathlib import Path

# Resolved relative to this file, so the loader works no matter which
# directory the app is started from (streamlit, uvicorn, scripts).
STYLE_FILE = Path(__file__).resolve().parent.parent / "style_examples" / "linkedin_style.txt"

_SECTION_SEPARATOR = "\n---\n"


@lru_cache(maxsize=1)
def _read_style_examples() -> str:
    return STYLE_FILE.read_text(encoding="utf-8")


def _section_heading(section: str) -> str:
    for line in section.splitlines():
        if line.strip():
            return line.strip().lower()
    return ""


def load_style_examples(exclude_headings: tuple[str, ...] = ()) -> str:
    """
    Returns the style guide, optionally with whole sections removed.

    Sections are separated by '---'. `exclude_headings` matches the start of a
    section's heading, e.g. ("formatting",) drops the FORMATTING block — which
    is redundant in the draft prompt because format_check_node now enforces
    those rules in code. Fewer prompt tokens = less Groq rate-limit waiting.
    """
    text = _read_style_examples()
    if not exclude_headings:
        return text

    kept = []
    for section in text.split(_SECTION_SEPARATOR):
        heading = _section_heading(section)
        if any(heading.startswith(prefix) for prefix in exclude_headings):
            continue
        kept.append(section)

    return _SECTION_SEPARATOR.join(kept)
