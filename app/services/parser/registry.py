"""File-extension → parser dispatch.

Each format-specific parser lives in its own module; the supported formats
are listed explicitly in `_PARSERS`.

Adding a new format:
  1. Create app/services/parser/<format>.py with a function that takes a
     Path and returns list[Passage].
  2. Import it here and add an entry to `_PARSERS` for each extension it
     claims (one parser can claim multiple).
"""

from collections.abc import Callable
from pathlib import Path

from app.schemas import Passage
from app.services.parser.markdown import parse_markdown

_FormatParser = Callable[[Path], list[Passage]]

_PARSERS: dict[str, _FormatParser] = {
    "md": parse_markdown,
    "markdown": parse_markdown,
}


def supported_extensions() -> list[str]:
    return sorted(_PARSERS)


def parse_file(path: str | Path) -> list[Passage]:
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(f"no parser registered for .{ext} (supported: {supported_extensions()})")
    return parser(p)


def parse_corpus(directory: str | Path) -> list[Passage]:
    """Parse every file in `directory` whose extension has a registered parser.

    Files with unregistered extensions (e.g. a stray README.txt or .DS_Store)
    are silently skipped so a single foreign file doesn't break ingest.
    """
    root = Path(directory)
    passages: list[Passage] = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower().lstrip(".") in _PARSERS:
            passages.extend(parse_file(path))
    return passages
