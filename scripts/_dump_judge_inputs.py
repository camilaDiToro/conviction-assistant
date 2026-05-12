"""Extract the minimal per-question payload the judge prompt needs
from a deterministic-run traces.jsonl. Output: one compact JSON per line.

Usage:
    uv run python scripts/_dump_judge_inputs.py <traces.jsonl>
"""

import json
import sys
from pathlib import Path


def _build_citations(result: dict) -> list[dict]:
    res = result.get("resolution") or {}
    entries = res.get("entries") or []
    out = []
    for i, e in enumerate(entries, start=1):
        out.append(
            {
                "marker": i,
                "passage_id": e.get("passage_id"),
                "document_title": e.get("document_title"),
                "heading_path": e.get("heading_path"),
                "passage_text": e.get("passage_text"),
                "anchored": e.get("failure_reason") is None,
            }
        )
    return out


def main() -> int:
    path = Path(sys.argv[1])
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            r = rec.get("result") or {}
            out_obj = r.get("output") or {}
            kind = out_obj.get("kind") or ""
            if kind == "answer":
                answer = out_obj.get("answer")
                clarifying = None
            else:
                answer = None
                clarifying = out_obj.get("question") or out_obj.get("clarifying_question")
            compact = {
                "id": rec["id"],
                "bucket": rec["bucket"],
                "language": rec["language"],
                "question": rec["question"],
                "expected_passage_ids": rec.get("expected_passage_ids", []),
                "expected_out_of_scope": rec.get("expected_out_of_scope"),
                "expected_general_knowledge": rec.get("expected_general_knowledge"),
                "expected_conflict_mention": rec.get("expected_conflict_mention"),
                "must_cite_at_least": rec.get("must_cite_at_least"),
                "output_kind": kind,
                "answer": answer,
                "clarifying_question": clarifying,
                "general_knowledge_used": out_obj.get("general_knowledge_used"),
                "general_knowledge_section": out_obj.get("general_knowledge_section"),
                "out_of_scope": out_obj.get("out_of_scope"),
                "conflict_detected": out_obj.get("conflict_detected"),
                "conflict_statement": out_obj.get("conflict_statement"),
                "citations": _build_citations(r),
            }
            print(json.dumps(compact, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
