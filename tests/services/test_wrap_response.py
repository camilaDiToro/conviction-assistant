"""Tests for app.services.wrap_response — the pure mapping layer."""

from datetime import UTC, date, datetime

from app.agent import (
    AgentResult,
    AnswerOutput,
    Citation,
    ClarifyingQuestionOutput,
    StepRecord,
)
from app.agent.resolver import CitationResolution, OffsetResolution
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


def _step_resolver(*, anchored: bool = True) -> StepRecord:
    entry = _resolution_entry(anchored=anchored)
    return StepRecord(
        step_id="step-r",
        kind="resolver",
        timestamp=datetime.now(UTC),
        payload={"entries": [entry.model_dump(mode="json")]},
    )


def _resolution_entry(*, anchored: bool = True) -> CitationResolution:
    text = "CDBs follow the tabela regressiva."
    start, end = (16, 33) if anchored else (None, None)
    return CitationResolution(
        passage_id="cdbs_quick_guide#tributacao",
        document_id="cdbs_quick_guide",
        document_title="CDBs Quick Guide",
        heading_path=["CDBs Quick Guide", "Tributação"],
        document_updated=date(2026, 4, 1),
        passage_text=text,
        start=start,
        end=end,
        failure_reason=None if anchored else "offset_not_found",
    )


def test_wrap_answer_maps_citation_document_to_filename() -> None:
    citation = Citation(passage_id="cdbs_quick_guide#tributacao", quote="tabela regressiva")
    entry = _resolution_entry(anchored=True)
    result = AgentResult(
        output=AnswerOutput(
            answer="The answer.",
            citations=[citation],
            general_knowledge_used=False,
            general_knowledge_section=None,
            out_of_scope=False,
        ),
        rewritten_question=None,
        language="en",
        steps=[_step_llm(), _step_resolver()],
        tool_call_count=1,
        search_count=1,
        resolution=OffsetResolution(entries=[entry]),
    )

    response, summary = wrap_response.wrap(
        result,
        language="en",
        conversation_id="conv",
        question_id="q",
        user_question="What is a CDB?",
        retriever_name="bm25",
    )

    assert isinstance(response, ChatAnswerResponse)
    citation_out = response.citations[0]
    assert citation_out.document == "cdbs_quick_guide.md"
    assert citation_out.heading == "Tributação"  # leaf of heading_path
    assert citation_out.passage_text == entry.passage_text
    assert citation_out.start == 16
    assert citation_out.end == 33
    assert response.disclaimer.startswith("This response is informational")
    # Two raw StepRecords + one synthetic response step appended for the drawer.
    assert response.usage_summary.step_count == 3
    assert response.debug.steps[-1].kind == "response"
    assert response.debug.steps[-1].result is not None
    assert response.debug.steps[-1].result["output"]["answer"] == "The answer."
    assert response.usage_summary.question_total_cost_usd > 0
    assert summary["language"] == "en"
    assert summary["retriever"] == "bm25"
    assert "resolution_entries" in summary


def test_wrap_clarify_branch_omits_citations() -> None:
    result = AgentResult(
        output=ClarifyingQuestionOutput(
            question="LCI or LCA?",
            options=["LCI", "LCA"],
        ),
        rewritten_question=None,
        language="en",
        steps=[_step_llm()],
        tool_call_count=0,
        search_count=0,
        resolution=None,
    )
    response, _ = wrap_response.wrap(
        result,
        language="pt",
        conversation_id="c",
        question_id="q",
        user_question="What is a CDB?",
        retriever_name="bm25",
    )
    assert isinstance(response, ChatClarifyResponse)
    assert response.question == "LCI or LCA?"
    assert response.options == ["LCI", "LCA"]
    assert response.disclaimer.startswith("Esta resposta é informativa")


def test_wrap_non_anchoring_citation_surfaces_with_null_offsets() -> None:
    entry = _resolution_entry(anchored=False)
    result = AgentResult(
        output=AnswerOutput(
            answer="Best-effort answer.",
            citations=[Citation(passage_id=entry.passage_id, quote="paraphrase")],
            general_knowledge_used=False,
            general_knowledge_section=None,
            out_of_scope=False,
        ),
        rewritten_question=None,
        language="en",
        steps=[_step_llm(), _step_resolver(anchored=False)],
        tool_call_count=0,
        search_count=1,
        resolution=OffsetResolution(entries=[entry]),
    )
    response, _ = wrap_response.wrap(
        result,
        language="en",
        conversation_id="c",
        question_id="q",
        user_question="What is a CDB?",
        retriever_name="bm25",
    )
    assert isinstance(response, ChatAnswerResponse)
    assert len(response.citations) == 1
    out = response.citations[0]
    assert out.start is None
    assert out.end is None
    assert out.passage_text == entry.passage_text


def test_wrap_prior_conversation_cost_is_added() -> None:
    result = AgentResult(
        output=ClarifyingQuestionOutput(question="?", options=["a", "b"]),
        rewritten_question=None,
        language="en",
        steps=[_step_llm()],
        tool_call_count=0,
        search_count=0,
        resolution=None,
    )
    response, _ = wrap_response.wrap(
        result,
        language="en",
        conversation_id="c",
        question_id="q",
        user_question="?",
        retriever_name="bm25",
        prior_conversation_cost_usd=0.001234,
    )
    summary = response.usage_summary
    assert summary.conversation_total_cost_usd > summary.question_total_cost_usd
