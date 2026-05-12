"""Loaders that bridge the deterministic trace artefacts and the judge.

``iter_judge_inputs`` reads a deterministic ``_traces.jsonl`` and yields
self-contained per-question records ready to feed to the judge prompt —
question, output, citations with full passage text, golden expectations.
No transformation of the agent's answer text (the judge needs ``[N]``
markers intact for ``citation_attribution``).

``load_judge_results`` reads a judge-emitted JSONL back into validated
:class:`JudgeResult` objects.

``prompt_hash`` produces a short, stable hash of the judge prompt for
the cross-model comparison contract.
"""

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from evals.judge.schema import JudgeResult


class JudgeCitation(BaseModel):
    """One cited passage as exposed to the judge.

    ``marker`` is the 1-indexed position the model expects in ``[N]``
    references inside ``answer`` (matches the order the agent emitted).
    """

    model_config = ConfigDict(extra="forbid")

    marker: int = Field(ge=1)
    passage_id: str
    document_id: str | None
    document_title: str | None
    heading_path: list[str] = Field(default_factory=list)
    passage_text: str
    anchored: bool


class JudgeInput(BaseModel):
    """Self-contained per-question payload for the judge.

    Mirrors what the prompt's "Inputs" section describes; the user pipes
    one of these (rendered as JSON or as the structured fields the
    prompt enumerates) into Claude alongside the prompt body.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    bucket: str
    language: str
    question: str
    expected_passage_ids: list[str] = Field(default_factory=list)
    expected_out_of_scope: bool
    expected_general_knowledge: bool
    expected_conflict_mention: bool
    must_cite_at_least: int
    output_kind: str
    answer: str | None
    clarifying_question: str | None
    general_knowledge_used: bool
    general_knowledge_section: str | None
    out_of_scope: bool
    citations: list[JudgeCitation] = Field(default_factory=list)


def prompt_hash(prompt_path: Path | str) -> str:
    """Stable 8-char sha256 prefix of the judge prompt file."""
    body = Path(prompt_path).read_bytes()
    return hashlib.sha256(body).hexdigest()[:8]


def iter_judge_inputs(traces_path: Path | str) -> Iterator[JudgeInput]:
    """Yield one :class:`JudgeInput` per record of a ``_traces.jsonl``.

    Skips error rows (records with ``error`` set and ``result=None``) —
    a judge cannot score something that never produced output.
    """
    path = Path(traces_path)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            judge_input = _build_input(raw)
            if judge_input is not None:
                yield judge_input


def _build_input(raw: dict[str, Any]) -> JudgeInput | None:
    result = raw.get("result")
    if not isinstance(result, dict):
        return None  # error row
    output = result.get("output") or {}
    kind = str(output.get("kind") or "")
    answer = output.get("answer") if kind == "answer" else None
    clarifying = output.get("question") if kind == "clarifying_question" else None

    entries = (result.get("resolution") or {}).get("entries") or []
    citations: list[JudgeCitation] = [
        JudgeCitation(
            marker=marker,
            passage_id=str(entry.get("passage_id") or ""),
            document_id=entry.get("document_id"),
            document_title=entry.get("document_title"),
            heading_path=list(entry.get("heading_path") or []),
            passage_text=str(entry.get("passage_text") or ""),
            anchored=entry.get("failure_reason") is None,
        )
        for marker, entry in enumerate(entries, start=1)
    ]

    return JudgeInput(
        id=str(raw["id"]),
        bucket=str(raw["bucket"]),
        language=str(raw["language"]),
        question=str(raw["question"]),
        expected_passage_ids=list(raw.get("expected_passage_ids") or []),
        expected_out_of_scope=bool(raw.get("expected_out_of_scope", False)),
        expected_general_knowledge=bool(raw.get("expected_general_knowledge", False)),
        expected_conflict_mention=bool(raw.get("expected_conflict_mention", False)),
        must_cite_at_least=int(raw.get("must_cite_at_least", 1)),
        output_kind=kind,
        answer=answer,
        clarifying_question=clarifying,
        general_knowledge_used=bool(output.get("general_knowledge_used", False)),
        general_knowledge_section=output.get("general_knowledge_section"),
        out_of_scope=bool(output.get("out_of_scope", False)),
        citations=citations,
    )


def load_judge_results(judge_path: Path | str) -> list[JudgeResult]:
    """Read a judge JSONL, validate every record against :class:`JudgeResult`."""
    path = Path(judge_path)
    results: list[JudgeResult] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                results.append(JudgeResult.model_validate_json(line))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"{path}:{line_no}: invalid judge record: {exc}") from exc
    return results


__all__ = [
    "JudgeCitation",
    "JudgeInput",
    "iter_judge_inputs",
    "load_judge_results",
    "prompt_hash",
]
