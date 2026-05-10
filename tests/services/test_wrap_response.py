"""Tests for app.services.wrap_response — the pure mapping layer."""

from datetime import UTC, date, datetime

from app.agent import (
    AgentResult,
    AnswerOutput,
    Citation,
    ClarifyingQuestionOutput,
    StepRecord,
)
from app.agent.verifier import VerifiedCitation
from app.api.schemas import ChatAnswerResponse, ChatClarifyResponse
from app.providers import TokenUsage
from app.services import wrap_response


def _step_llm() -> StepRecord:
    return StepRecord(
        step_id="step-1",
        kind="llm_call",
        timestamp=datetime.now(UTC),
        payload={"stage": "agent_loop", "finish_reason": "stop", "tool_calls": []},
        usage=TokenUsage(model="gpt-5", prompt_tokens=100, completion_tokens=20),
    )


def _step_verifier(*, all_passed: bool = True) -> StepRecord:
    return StepRecord(
        step_id="step-v",
        kind="verifier",
        timestamp=datetime.now(UTC),
        payload={
            "attempt": 0,
            "all_passed": all_passed,
            "verified": [],
            "failures": [],
        },
    )


def _verified_cit() -> VerifiedCitation:
    return VerifiedCitation(
        passage_id="cdbs_quick_guide#tributacao",
        document_id="cdbs_quick_guide",
        document_title="CDBs Quick Guide",
        heading_path=["CDBs Quick Guide", "Tributação"],
        document_updated=date(2026, 4, 1),
        quote="tabela regressiva",
    )


def test_wrap_answer_maps_citation_document_to_filename() -> None:
    citation = Citation(passage_id="cdbs_quick_guide#tributacao", quote="tabela regressiva")
    result = AgentResult(
        output=AnswerOutput(
            answer="The answer.",
            citations=[citation],
            general_knowledge_used=False,
            general_knowledge_section=None,
            out_of_scope=False,
        ),
        rewritten_question=None,
        steps=[_step_llm(), _step_verifier()],
        tool_call_count=1,
        search_count=1,
        verified_citations=[_verified_cit()],
    )

    response, summary = wrap_response.wrap(
        result,
        language="en",
        conversation_id="conv",
        question_id="q",
        user_question="What is a CDB?",
        retriever_name="bm25",
        verifier_name="substring",
    )

    assert isinstance(response, ChatAnswerResponse)
    assert response.citations[0].document == "cdbs_quick_guide.md"
    assert response.citations[0].heading == "Tributação"  # leaf of heading_path
    assert response.citations[0].quote == "tabela regressiva"
    assert response.disclaimer.startswith("This response is informational")
    assert response.usage_summary.step_count == 2
    assert response.usage_summary.question_total_cost_usd > 0
    assert response.debug.verification_passed is True
    assert summary["language"] == "en"
    assert summary["retriever"] == "bm25"
    assert summary["verifier_strategy"] == "substring"


def test_wrap_clarify_branch_omits_citations() -> None:
    result = AgentResult(
        output=ClarifyingQuestionOutput(
            question="LCI or LCA?",
            options=["LCI", "LCA"],
        ),
        rewritten_question=None,
        steps=[_step_llm()],
        tool_call_count=0,
        search_count=0,
        verified_citations=None,
    )
    response, _ = wrap_response.wrap(
        result,
        language="pt",
        conversation_id="c",
        question_id="q",
        user_question="What is a CDB?",
        retriever_name="bm25",
        verifier_name="substring",
    )
    assert isinstance(response, ChatClarifyResponse)
    assert response.question == "LCI or LCA?"
    assert response.options == ["LCI", "LCA"]
    assert response.disclaimer.startswith("Esta resposta é informativa")
    # No citations field on ClarifyResponse — verifier passed trivially.
    assert response.debug.verification_passed is True


def test_wrap_verifier_failure_reflected_in_debug() -> None:
    result = AgentResult(
        output=AnswerOutput(
            answer="Stripped.",
            citations=[],
            general_knowledge_used=False,
            general_knowledge_section=None,
            out_of_scope=False,
        ),
        rewritten_question=None,
        steps=[_step_llm(), _step_verifier(all_passed=False), _step_verifier(all_passed=False)],
        tool_call_count=0,
        search_count=1,
        verified_citations=[],
    )
    response, summary = wrap_response.wrap(
        result,
        language="en",
        conversation_id="c",
        question_id="q",
        user_question="What is a CDB?",
        retriever_name="bm25",
        verifier_name="substring",
    )
    assert isinstance(response, ChatAnswerResponse)
    assert response.debug.verification_passed is False
    assert summary["verifier_passed"] is False


def test_wrap_prior_conversation_cost_is_added() -> None:
    result = AgentResult(
        output=ClarifyingQuestionOutput(question="?", options=["a", "b"]),
        rewritten_question=None,
        steps=[_step_llm()],
        tool_call_count=0,
        search_count=0,
        verified_citations=None,
    )
    response, _ = wrap_response.wrap(
        result,
        language="en",
        conversation_id="c",
        question_id="q",
        user_question="?",
        retriever_name="bm25",
        verifier_name="substring",
        prior_conversation_cost_usd=0.001234,
    )
    summary = response.usage_summary
    assert summary.conversation_total_cost_usd > summary.question_total_cost_usd
