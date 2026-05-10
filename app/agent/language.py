"""PT / ES / EN language detection for agent-side localization.

Used today by the safe-refusal path in `app.agent.retry_policy` (and
formerly inline in `app.agent.loop`). B9 will grow this into the
disclaimer-language path; the public function signature stays
`detect_language(text: str) -> Literal["pt", "es", "en"]`.

Heuristic: a small set of language-distinctive markers (function words +
diacritic patterns) on lowercased text. Defaults to ``"en"``.
"""

from typing import Literal

_PT_MARKERS = (" não ", " você ", " está ", " são ", " é ", " da ", " do ", "ção", "ões")
_ES_MARKERS = (" no ", " usted ", " está ", " son ", " es ", " del ", "ción", " ¿", "¡", " ñ")


def detect_language(text: str) -> Literal["pt", "es", "en"]:
    """Classify ``text`` as PT, ES, or EN. Defaults to EN when no markers hit."""
    lower = f" {text.lower()} "
    pt_score = sum(m in lower for m in _PT_MARKERS)
    es_score = sum(m in lower for m in _ES_MARKERS)
    if pt_score == 0 and es_score == 0:
        return "en"
    if pt_score >= es_score:
        return "pt"
    return "es"


__all__ = ["detect_language"]
