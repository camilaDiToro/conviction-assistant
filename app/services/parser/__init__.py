"""Parser package.

Generic file-extension dispatcher. Each format-specific parser lives in its
own module and registers itself with @register("<ext>").

Adding a new format:
  1. Create app/services/parser/<format>.py with a function that takes a
     Path and returns list[Passage].
  2. Decorate it with @register("<ext>", ...). One parser can claim
     multiple extensions.
  3. Import the module at the bottom of this file so registration runs
     at import time.

Adding a new language for detection: edit STOPWORDS in
app/services/parser/text.py.
"""

from collections.abc import Callable
from pathlib import Path

from app.schemas import Passage

_FormatParser = Callable[[Path], list[Passage]]
_PARSERS: dict[str, _FormatParser] = {}


def register(*extensions: str) -> Callable[[_FormatParser], _FormatParser]:
    """Register a parser function for one or more file extensions."""

    def decorator(fn: _FormatParser) -> _FormatParser:
        for ext in extensions:
            _PARSERS[ext.lower().lstrip(".")] = fn
        return fn

    return decorator


def supported_extensions() -> list[str]:
    return sorted(_PARSERS)


def parse_file(path: str | Path) -> list[Passage]:
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(
            f"no parser registered for .{ext} (supported: {supported_extensions()})"
        )
    return parser(p)


def parse_corpus(directory: str | Path) -> list[Passage]:
    """Parse every file in `directory` whose extension has a registered parser."""
    root = Path(directory)
    passages: list[Passage] = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower().lstrip(".") in _PARSERS:
            passages.extend(parse_file(path))
    return passages


# Format parsers self-register on import. New ones go here.
from app.services.parser import markdown  # noqa: E402, F401

__all__ = [
    "parse_corpus",
    "parse_file",
    "register",
    "supported_extensions",
]
