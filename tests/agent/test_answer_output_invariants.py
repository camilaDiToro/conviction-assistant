"""Unit tests for the AnswerOutput inter-field invariants enforced by
``@model_validator``."""

import pytest
from pydantic import ValidationError

from app.agent.schemas import AnswerOutput, Citation


def _valid_answer(**overrides) -> dict:
    base = dict(
        answer="a",
        citations=[Citation(passage_id="p", quote="q")],
        general_knowledge_used=False,
        general_knowledge_section=None,
        out_of_scope=False,
    )
    base.update(overrides)
    return base


def test_answer_output_accepts_consistent_general_knowledge() -> None:
    out = AnswerOutput(
        **_valid_answer(
            general_knowledge_used=True,
            general_knowledge_section="Not from Decade convictions — ...",
        )
    )
    assert out.general_knowledge_used
    assert out.general_knowledge_section is not None


def test_answer_output_rejects_used_without_section() -> None:
    with pytest.raises(ValidationError, match="non-empty general_knowledge_section"):
        AnswerOutput(**_valid_answer(general_knowledge_used=True, general_knowledge_section=None))


def test_answer_output_rejects_used_with_blank_section() -> None:
    with pytest.raises(ValidationError, match="non-empty general_knowledge_section"):
        AnswerOutput(**_valid_answer(general_knowledge_used=True, general_knowledge_section="   "))


def test_answer_output_rejects_section_without_used_flag() -> None:
    with pytest.raises(ValidationError, match="general_knowledge_used=true"):
        AnswerOutput(
            **_valid_answer(general_knowledge_used=False, general_knowledge_section="text")
        )


def test_answer_output_rejects_out_of_scope_with_citations() -> None:
    with pytest.raises(ValidationError, match="out_of_scope=true requires empty citations"):
        AnswerOutput(**_valid_answer(out_of_scope=True))


def test_answer_output_accepts_out_of_scope_with_empty_citations() -> None:
    out = AnswerOutput(**_valid_answer(out_of_scope=True, citations=[]))
    assert out.out_of_scope
    assert out.citations == []


def test_answer_output_accepts_consistent_conflict() -> None:
    out = AnswerOutput(
        **_valid_answer(
            conflict_detected=True,
            conflict_statement="As convicções divergem sobre come-cotas e CDB.",
        )
    )
    assert out.conflict_detected
    assert out.conflict_statement is not None


def test_answer_output_rejects_conflict_detected_without_statement() -> None:
    with pytest.raises(ValidationError, match="non-empty conflict_statement"):
        AnswerOutput(**_valid_answer(conflict_detected=True, conflict_statement=None))


def test_answer_output_rejects_conflict_detected_with_blank_statement() -> None:
    with pytest.raises(ValidationError, match="non-empty conflict_statement"):
        AnswerOutput(**_valid_answer(conflict_detected=True, conflict_statement="   "))


def test_answer_output_rejects_statement_without_conflict_flag() -> None:
    with pytest.raises(ValidationError, match="conflict_detected=true"):
        AnswerOutput(
            **_valid_answer(conflict_detected=False, conflict_statement="convictions disagree")
        )


def test_answer_output_conflict_defaults_to_false() -> None:
    out = AnswerOutput(**_valid_answer())
    assert out.conflict_detected is False
    assert out.conflict_statement is None
