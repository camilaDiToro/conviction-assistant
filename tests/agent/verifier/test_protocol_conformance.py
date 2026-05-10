"""Parametrized conformance suite for every registered :class:`Verifier`.

Today only ``substring`` is registered; the parametrization is the
seam for tomorrow — when a second strategy lands, every test here
runs against both with no copy-paste.

The contract these tests pin (see ``docs/ARCHITECTURES.md``):

- Verbatim quote → ``all_passed`` True; the citation appears in ``verified``.
- Paraphrase → fails with ``substring_not_found``.
- Empty quote → fails with ``empty_quote``.
- Unknown passage_id → fails with ``passage_not_found``.

Any future verifier strategy must preserve these binary outcomes (no
soft confidence scores). The substring guarantee is the architectural
commitment.
"""

from datetime import date

import pytest

from app.agent.schemas import AnswerOutput, Citation
from app.agent.verifier import VERIFIERS, Verifier
from app.schemas.passage import Passage


def _passage(
    passage_id: str = "doc#sec",
    text: str = "CDBs follow the regressive IR table.",
) -> Passage:
    return Passage(
        id=passage_id,
        document_id=passage_id.split("#")[0],
        document_title="Doc",
        heading=passage_id.split("#", 1)[-1],
        heading_path=[passage_id.split("#", 1)[-1]],
        text=text,
        document_updated=date(2026, 4, 1),
    )


def _answer(citations: list[Citation]) -> AnswerOutput:
    return AnswerOutput(
        answer="x",
        citations=citations,
        general_knowledge_used=False,
        general_knowledge_section=None,
        out_of_scope=False,
    )


@pytest.fixture(params=sorted(VERIFIERS))
def verifier(request: pytest.FixtureRequest) -> Verifier:
    """Yield each registered verifier strategy in turn."""
    return VERIFIERS[request.param]()


def test_verbatim_quote_passes(verifier: Verifier) -> None:
    p = _passage(text="CDBs follow the regressive IR table.")
    answer = _answer([Citation(passage_id=p.id, quote="regressive IR table")])
    result = verifier.verify(answer, {p.id: p})
    assert result.all_passed
    assert len(result.verified) == 1
    assert result.verified[0].quote == "regressive IR table"


def test_paraphrase_fails(verifier: Verifier) -> None:
    p = _passage(text="CDBs follow the regressive IR table.")
    answer = _answer([Citation(passage_id=p.id, quote="regressive table for IR")])
    result = verifier.verify(answer, {p.id: p})
    assert not result.all_passed
    assert len(result.failures) == 1
    assert result.failures[0].reason == "substring_not_found"


def test_empty_quote_fails(verifier: Verifier) -> None:
    p = _passage()
    answer = _answer([Citation(passage_id=p.id, quote="")])
    result = verifier.verify(answer, {p.id: p})
    assert not result.all_passed
    assert result.failures[0].reason == "empty_quote"


def test_unknown_passage_id_fails(verifier: Verifier) -> None:
    answer = _answer([Citation(passage_id="missing#sec", quote="anything")])
    result = verifier.verify(answer, {})
    assert not result.all_passed
    assert result.failures[0].reason == "passage_not_found"
