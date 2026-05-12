"""Unit tests for AgentResult.token_totals."""

from datetime import UTC, datetime

from app.agent.schemas import (
    AgentResult,
    AnswerOutput,
    Citation,
    StepRecord,
    TokenTotals,
)
from app.providers import TokenUsage


def _result(steps: list[StepRecord]) -> AgentResult:
    return AgentResult(
        output=AnswerOutput(
            answer="a",
            citations=[Citation(passage_id="p", quote="q")],
            general_knowledge_used=False,
            general_knowledge_section=None,
            out_of_scope=False,
        ),
        rewritten_question=None,
        language="en",
        steps=steps,
        tool_call_count=0,
        search_count=0,
    )


def _llm_step(*, prompt: int, completion: int, cached: int = 0, reasoning: int = 0) -> StepRecord:
    return StepRecord(
        step_id="s",
        kind="llm_call",
        timestamp=datetime.now(UTC),
        payload={},
        usage=TokenUsage(
            model="stub",
            prompt_tokens=prompt,
            completion_tokens=completion,
            cached_tokens=cached,
            reasoning_tokens=reasoning,
        ),
    )


def _tool_step() -> StepRecord:
    return StepRecord(
        step_id="t",
        kind="tool_call",
        timestamp=datetime.now(UTC),
        payload={},
        tool_name="search_convictions",
    )


def test_token_totals_sums_llm_call_usages_only() -> None:
    res = _result(
        [
            _llm_step(prompt=10, completion=5, cached=2, reasoning=1),
            _tool_step(),  # ignored (no usage, wrong kind)
            _llm_step(prompt=20, completion=8, cached=4, reasoning=3),
        ]
    )
    assert res.token_totals == TokenTotals(
        llm_call_count=2,
        prompt_tokens=30,
        completion_tokens=13,
        cached_tokens=6,
        reasoning_tokens=4,
    )


def test_token_totals_zero_on_empty_steps() -> None:
    totals = _result([]).token_totals
    assert totals.llm_call_count == 0
    assert totals.prompt_tokens == 0
    assert totals.completion_tokens == 0
