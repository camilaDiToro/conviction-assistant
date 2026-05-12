"""Compact per-question judge-input summary (drop passage_text)."""

import json
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1])
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            r = rec.get("result") or {}
            out_obj = r.get("output") or {}
            kind = out_obj.get("kind") or ""
            res = r.get("resolution") or {}
            cits = []
            for i, e in enumerate(res.get("entries") or [], start=1):
                cits.append({
                    "m": i,
                    "pid": e.get("passage_id"),
                    "doc": e.get("document_title"),
                    "anch": e.get("failure_reason") is None,
                })
            print(json.dumps({
                "id": rec["id"],
                "bucket": rec["bucket"],
                "lang": rec["language"],
                "q": rec["question"],
                "exp_oos": rec.get("expected_out_of_scope"),
                "exp_gk": rec.get("expected_general_knowledge"),
                "exp_conflict": rec.get("expected_conflict_mention"),
                "exp_pids": rec.get("expected_passage_ids", []),
                "kind": kind,
                "answer": out_obj.get("answer"),
                "clar": out_obj.get("question") or out_obj.get("clarifying_question"),
                "gk_used": out_obj.get("general_knowledge_used"),
                "gk_sec": out_obj.get("general_knowledge_section"),
                "oos": out_obj.get("out_of_scope"),
                "conf": out_obj.get("conflict_detected"),
                "conf_stmt": out_obj.get("conflict_statement"),
                "cits": cits,
            }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
