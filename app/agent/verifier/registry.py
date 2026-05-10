"""Verifier strategy registry.

A new verifier strategy registers itself via the ``@register('name')``
decorator at module import. :func:`get_verifier` looks up the chosen
strategy by name (typically from ``settings.verifier_strategy``).

The substring guarantee is the architectural commitment of this
project — adding a second strategy is a deliberate code change, not a
``.env`` flip. The single-member ``Literal`` in :mod:`app.config.settings`
enforces that property.
"""

from collections.abc import Callable

from app.agent.verifier.base import Verifier

VERIFIERS: dict[str, Callable[[], Verifier]] = {}


def register(name: str) -> Callable[[Callable[[], Verifier]], Callable[[], Verifier]]:
    """Register a Verifier factory under ``name``. Used at module import."""

    def decorator(factory: Callable[[], Verifier]) -> Callable[[], Verifier]:
        if name in VERIFIERS:
            raise ValueError(f"verifier {name!r} already registered")
        VERIFIERS[name] = factory
        return factory

    return decorator


def get_verifier(name: str) -> Verifier:
    """Instantiate the registered verifier named ``name``."""
    if name not in VERIFIERS:
        available = ", ".join(sorted(VERIFIERS)) or "<none>"
        raise ValueError(f"unknown verifier {name!r}; available: {available}")
    return VERIFIERS[name]()


__all__ = ["VERIFIERS", "get_verifier", "register"]
