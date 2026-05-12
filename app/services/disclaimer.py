"""Localized disclaimer strings.

Three frozen strings, keyed by detected language. Lifted from
``frontend/src/lib/mock-chat.ts`` so the mock and backend stay aligned.
The disclaimer is always appended by the orchestrator, never by
the model — this is the only way to guarantee it shows up.
"""

from app.i18n import Language

_DISCLAIMERS: dict[Language, str] = {
    "pt": "Esta resposta é informativa e não constitui recomendação de investimento.",
    "en": "This response is informational and does not constitute investment advice.",
    "es": "Esta respuesta es informativa y no constituye una recomendación de inversión.",
}


def disclaimer_for(language: Language) -> str:
    return _DISCLAIMERS[language]


__all__ = ["disclaimer_for"]
