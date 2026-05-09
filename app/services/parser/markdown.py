"""Markdown parser.

A passage is one ## section. The first ^# line is the document title (not a
passage). Subsections (### +) stay inline inside their parent passage's text.

Passage ID = "<document_id>#<slug-of-heading>". On heading collisions within
the same document, the second occurrence becomes "<base>-2", third "-3", etc.
"""

import re
from pathlib import Path

from app.schemas import Passage
from app.services.parser import register
from app.services.parser.dates import extract_updated
from app.services.parser.text import slugify

_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_H2_LINE_RE = re.compile(r"^##(?!#)\s+(.+?)\s*$")


def _split_sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in body.splitlines():
        m = _H2_LINE_RE.match(line)
        if m:
            if current_heading is not None:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = m.group(1)
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return sections


@register("md", "markdown")
def parse_markdown(path: Path) -> list[Passage]:
    raw = path.read_text(encoding="utf-8")
    document_id = path.stem

    title_match = _H1_RE.search(raw)
    document_title = title_match.group(1).strip() if title_match else document_id
    document_updated = extract_updated(raw)

    seen_slugs: dict[str, int] = {}
    passages: list[Passage] = []
    for heading, text in _split_sections(raw):
        base = slugify(heading) or "section"
        seen_slugs[base] = seen_slugs.get(base, 0) + 1
        slug = base if seen_slugs[base] == 1 else f"{base}-{seen_slugs[base]}"
        passages.append(
            Passage(
                id=f"{document_id}#{slug}",
                document_id=document_id,
                document_title=document_title,
                heading=heading,
                heading_path=[document_title, heading],
                text=text,
                document_updated=document_updated,
            )
        )
    return passages
