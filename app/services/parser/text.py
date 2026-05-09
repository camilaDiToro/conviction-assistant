"""Cross-format text utilities used by every format parser.

Right now this is just slugify (used to build stable passage IDs from
human-readable headings). When a future format parser needs another shared
helper, add it here rather than duplicating it in the format module.
"""

import re
import unicodedata


def slugify(text: str) -> str:
    """Build a stable, URL/ID-safe slug from a heading.

    Pipeline: NFKD-normalize → drop combining marks (strips accents) →
    lowercase → replace non-alphanumeric runs with '-' → strip edge dashes.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    no_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    dashed = re.sub(r"[^a-z0-9]+", "-", no_marks.lower())
    return dashed.strip("-")
