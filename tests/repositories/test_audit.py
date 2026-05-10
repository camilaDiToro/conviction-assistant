"""Tests for app.repositories.audit — round-trips through audit_log + cost_log."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import db
from app.repositories import audit as audit_repo


@pytest.fixture
async def session(tmp_path: Path):
    db_path = tmp_path / "audit_repo.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


def _row(
    *,
    step_id: str,
    conversation_id: str = "conv-1",
    question_id: str = "q-1",
    kind: str = "llm_call",
    timestamp: str | None = None,
    payload: str = "{}",
    usage: str | None = None,
) -> audit_repo.AuditRow:
    return audit_repo.AuditRow(
        step_id=step_id,
        question_id=question_id,
        conversation_id=conversation_id,
        timestamp=timestamp or datetime.now(UTC).isoformat(),
        kind=kind,
        payload=payload,
        usage=usage,
    )


async def test_insert_and_fetch_round_trip(session) -> None:
    usage_json = '{"model":"gpt-5","prompt_tokens":1,"completion_tokens":1}'
    rows = [
        _row(step_id="s1", kind="llm_call", usage=usage_json),
        _row(step_id="s2", kind="tool_call"),
        _row(step_id="s3", kind="response"),
    ]
    n = await audit_repo.insert_many(session, rows)
    await session.commit()
    assert n == 3

    fetched = await audit_repo.fetch_by_conversation(session, "conv-1")
    assert len(fetched) == 3
    assert {r["step_id"] for r in fetched} == {"s1", "s2", "s3"}


async def test_fetch_unknown_conversation_returns_empty(session) -> None:
    rows = await audit_repo.fetch_by_conversation(session, "does-not-exist")
    assert rows == []


async def test_cost_log_view_filters_to_llm_calls(session) -> None:
    """The cost_log view selects only kind='llm_call' rows."""
    u1 = '{"model":"gpt-5","prompt_tokens":10,"completion_tokens":2}'
    u5 = '{"model":"gpt-5","prompt_tokens":50,"completion_tokens":3}'
    rows = [
        _row(step_id="s1", kind="llm_call", usage=u1),
        _row(step_id="s2", kind="tool_call"),
        _row(step_id="s3", kind="verifier"),
        _row(step_id="s4", kind="response"),
        _row(step_id="s5", kind="llm_call", usage=u5),
    ]
    await audit_repo.insert_many(session, rows)
    await session.commit()

    cost_rows = await audit_repo.fetch_cost_rows_by_conversation(session, "conv-1")
    assert {r["step_id"] for r in cost_rows} == {"s1", "s5"}
    assert all(r["kind"] == "llm_call" for r in cost_rows)
