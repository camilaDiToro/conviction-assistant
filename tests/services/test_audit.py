"""Tests for app.services.audit — the audit-log writer."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.agent.schemas import StepRecord
from app.config import db
from app.providers import TokenUsage
from app.repositories import audit as audit_repo
from app.services import audit as audit_service


@pytest.fixture
async def session(tmp_path: Path):
    db_path = tmp_path / "audit_test.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


def _step(kind: str = "llm_call", *, with_usage: bool = True) -> StepRecord:
    return StepRecord(
        step_id=f"step-{kind}-{datetime.now(UTC).timestamp()}",
        kind=kind,  # type: ignore[arg-type]
        timestamp=datetime.now(UTC),
        payload={"stage": "agent_loop", "finish_reason": "stop", "tool_calls": []},
        usage=TokenUsage(
            model="gpt-5",
            prompt_tokens=100,
            completion_tokens=20,
            cached_tokens=0,
        )
        if with_usage and kind == "llm_call"
        else None,
        tool_name=None,
    )


async def test_persist_question_writes_steps_plus_response_row(session) -> None:
    steps = [_step("llm_call"), _step("tool_call", with_usage=False)]
    n = await audit_service.persist_question(
        session,
        conversation_id="conv-1",
        question_id="q-1",
        steps=steps,
        response_summary={"language": "en", "verifier_passed": True},
    )
    # 2 steps + 1 response summary row
    assert n == 3

    rows = await audit_repo.fetch_by_conversation(session, "conv-1")
    assert len(rows) == 3
    kinds = [r["kind"] for r in rows]
    # Order isn't asserted; just the set + count.
    assert "response" in kinds
    assert kinds.count("llm_call") == 1
    assert kinds.count("tool_call") == 1


async def test_persist_question_groups_by_conversation_id(session) -> None:
    """Two separate /chat calls in the same conversation_id are queryable
    together; an unrelated conversation is isolated.
    """
    await audit_service.persist_question(
        session,
        conversation_id="conv-A",
        question_id="qA1",
        steps=[_step("llm_call")],
        response_summary={"language": "en"},
    )
    await audit_service.persist_question(
        session,
        conversation_id="conv-A",
        question_id="qA2",
        steps=[_step("llm_call")],
        response_summary={"language": "en"},
    )
    await audit_service.persist_question(
        session,
        conversation_id="conv-B",
        question_id="qB1",
        steps=[_step("llm_call")],
        response_summary={"language": "en"},
    )

    a_rows = await audit_repo.fetch_by_conversation(session, "conv-A")
    b_rows = await audit_repo.fetch_by_conversation(session, "conv-B")
    assert len(a_rows) == 4  # 2 steps + 2 response rows
    assert len(b_rows) == 2  # 1 step + 1 response row


async def test_persist_question_failure_does_not_raise(
    session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the insert raises, the service swallows it and returns 0 — the
    caller never sees an error from audit-write failures.
    """

    async def boom(*_args, **_kwargs) -> int:
        raise RuntimeError("simulated DB failure")

    monkeypatch.setattr(audit_repo, "insert_many", boom)

    n = await audit_service.persist_question(
        session,
        conversation_id="conv-x",
        question_id="q-x",
        steps=[_step("llm_call")],
        response_summary={"language": "en"},
    )
    assert n == 0
