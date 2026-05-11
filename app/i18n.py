"""Language primitives shared across api, agent, services, and evals.

Top-level (like :mod:`app.errors`) because the supported set of UI
languages is a cross-cutting domain primitive, not a layered concern.
Keeping the alias here avoids importing service or agent modules just
to reach for the type.
"""

from typing import Literal, get_args

Language = Literal["pt", "es", "en"]

SUPPORTED_LANGUAGES: frozenset[Language] = frozenset(get_args(Language))

__all__ = ["Language", "SUPPORTED_LANGUAGES"]
