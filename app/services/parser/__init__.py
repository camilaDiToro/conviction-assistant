"""Parser package — re-exports the public dispatch API.

See `app/services/parser/registry.py` for the format registry and dispatcher;
each format lives in its own module (e.g. `markdown.py`).
"""

from app.services.parser.registry import parse_corpus, parse_file, supported_extensions

__all__ = [
    "parse_corpus",
    "parse_file",
    "supported_extensions",
]
