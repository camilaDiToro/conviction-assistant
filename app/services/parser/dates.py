"""Extract an "Updated" / "Atualizado" date from document text.

This is a deliberately simple v1: a single regex that catches the common
PT/EN phrasings (with or without "de", italic/bold/plain). When multiple
markers exist in one file, the last match wins; when none is present it
returns None.

Ideas for a stronger version:
- Move per-document metadata into a YAML/TOML frontmatter block, so the
  date is a structured field instead of scattered prose.
- Fall back to a small LLM call when the regex doesn't find a marker, to
  catch novel phrasings without growing the regex.
- Use the file's last git commit date as a secondary signal when no
  in-document marker exists.
"""

import re
from datetime import date

PT_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
EN_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
ALL_MONTHS = PT_MONTHS | EN_MONTHS

_LABEL = r"(?:[Úú]ltima\s+Atualiza[çc][ãa]o|Last\s+Updated|Atualiza[çc][ãa]o|Atualizado|Updated)"
_DATE_RE = re.compile(
    rf"{_LABEL}\s*:\s*(?P<month>[A-Za-zçÇãÃõÕêÊéÉ]+)\s+(?:de\s+)?(?P<year>\d{{4}})",
    re.IGNORECASE,
)


def extract_updated(text: str) -> date | None:
    """Return the LAST Updated date found anywhere in the text, or None."""
    last: date | None = None
    for m in _DATE_RE.finditer(text):
        month_name = m.group("month").lower()
        if month_name not in ALL_MONTHS:
            continue
        try:
            last = date(int(m.group("year")), ALL_MONTHS[month_name], 1)
        except ValueError:
            continue
    return last
