"""Bundle the latest eval run (0007) into a TS file consumed by the design site.

Reads three sources from evals/results/0007/:
  - 2026-05-12_14-44-51_combined_openai_gpt-5.5_low.csv  (deterministic metrics)
  - per-question *_id-qNN_traces.jsonl                    (Q&A + resolved citations)
  - judge/all_judges.jsonl                                (LLM-as-judge rubrics)

Emits frontend/src/data/eval_mock.ts with EVAL_MOCK[] + EVAL_MOCK_META.
"""

import csv
import glob
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = REPO_ROOT / "evals" / "results" / "0007"
COMBINED_CSV = RUN_DIR / "2026-05-12_14-44-51_combined_openai_gpt-5.5_low.csv"
JUDGE_FILE = RUN_DIR / "judge" / "all_judges.jsonl"
OUT = REPO_ROOT / "frontend" / "src" / "data" / "eval_mock.ts"

DET_METRICS = [
    "anchor_rate",
    "citation_precision",
    "citation_recall",
    "refusal_correctness",
    "general_knowledge_correctness",
    "clarify_correctness",
    "meets_min_citations",
    "conflict_min_citations",
    "language_match",
]

JUDGE_RUBRICS = [
    "faithfulness",
    "answer_relevancy",
    "conflict_disclosure",
    "rule_a_purity",
    "citation_attribution",
    "completeness",
]


def latest_trace_per_question() -> dict[str, Path]:
    by_qid: dict[str, Path] = {}
    for p in glob.glob(str(RUN_DIR / "*_id-q*_traces.jsonl")):
        path = Path(p)
        # filename format: <timestamp>_..._id-qNN_traces.jsonl
        name = path.name
        # qid lives between '_id-' and '_traces.jsonl'
        qid = name.split("_id-")[1].rsplit("_traces.jsonl", 1)[0]
        ts = name.split("_")[0] + "_" + name.split("_")[1]  # date + time
        prev = by_qid.get(qid)
        if prev is None or prev.name < name:
            by_qid[qid] = path
        _ = ts  # noqa
    return by_qid


def load_det_metrics() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    with open(COMBINED_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics = []
            for name in DET_METRICS:
                label = row.get(name, "") or ""
                reason = row.get(f"{name}_reason", "") or ""
                metrics.append({"name": name, "label": label, "reason": reason})
            out[row["id"]] = metrics
    return out


def load_judge() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    with open(JUDGE_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            rubrics = []
            for name in JUDGE_RUBRICS:
                r = rec.get(name) or {}
                applicable = bool(r.get("applicable", True)) if "applicable" in r else r.get("label") != "n/a"
                rubrics.append(
                    {
                        "name": name,
                        "score": r.get("score"),
                        "label": r.get("label"),
                        "reason": r.get("reason") or "",
                        "applicable": applicable,
                    }
                )
            out[rec["id"]] = rubrics
    return out


def resolver_entries(trace: dict) -> list[dict]:
    steps = trace.get("result", {}).get("steps", []) or []
    for step in reversed(steps):
        if step.get("kind") == "resolver":
            return step.get("payload", {}).get("entries", []) or []
    return []


def build_citations(trace: dict) -> list[dict]:
    """Map resolver entries → frontend Citation[] shape."""
    out = []
    for e in resolver_entries(trace):
        heading_path = e.get("heading_path") or []
        out.append(
            {
                "passage_id": e["passage_id"],
                "document": e.get("document_title", ""),
                "heading": heading_path[-1] if heading_path else "",
                "heading_path": heading_path,
                "passage_text": e.get("passage_text", ""),
                "start": e.get("start"),
                "end": e.get("end"),
            }
        )
    return out


def build_turns(trace: dict, citations: list[dict]) -> list[dict]:
    turns: list[dict] = []
    for pt in trace.get("prior_turns", []) or []:
        turns.append({"role": pt["role"], "content": pt.get("content", "")})
    turns.append({"role": "user", "content": trace["question"]})

    out = trace.get("result", {}).get("output", {}) or {}
    kind = out.get("kind")
    if kind == "clarifying_question":
        response = {
            "kind": "clarifying_question",
            "question": out.get("question", ""),
            "options": out.get("options", []) or [],
        }
    else:
        response = {
            "kind": "answer",
            "answer": out.get("answer", ""),
            "citations": citations,
            "general_knowledge_used": bool(out.get("general_knowledge_used", False)),
            "general_knowledge_section": out.get("general_knowledge_section"),
            "out_of_scope": bool(out.get("out_of_scope", False)),
            "conflict_detected": bool(out.get("conflict_detected", False)),
            "conflict_statement": out.get("conflict_statement"),
        }
    turns.append({"role": "assistant", "response": response})
    return turns


def build_record(trace: dict, det: list[dict], judge: list[dict]) -> dict:
    citations = build_citations(trace)
    return {
        "id": trace["id"],
        "bucket": trace["bucket"],
        "language": trace["language"],
        "question": trace["question"],
        "expected": {
            "passage_ids": trace.get("expected_passage_ids", []) or [],
            "out_of_scope": bool(trace.get("expected_out_of_scope", False)),
            "general_knowledge": bool(trace.get("expected_general_knowledge", False)),
            "conflict_mention": bool(trace.get("expected_conflict_mention", False)),
            "must_cite_at_least": int(trace.get("must_cite_at_least", 1) or 0),
        },
        "duration_ms": int(trace.get("duration_ms", 0) or 0),
        "turns": build_turns(trace, citations),
        "deterministic": det,
        "judge": judge,
    }


def emit_ts(records: list[dict], meta: dict) -> str:
    header = '''// AUTO-GENERATED by scripts/build_eval_mock.py — do not edit by hand.
// Source: evals/results/0007/ (deterministic + LLM-as-judge run).

export interface EvalCitation {
  passage_id: string
  document: string
  heading: string
  heading_path: string[]
  passage_text: string
  start: number | null
  end: number | null
}

export interface EvalAnswerResponse {
  kind: 'answer'
  answer: string
  citations: EvalCitation[]
  general_knowledge_used: boolean
  general_knowledge_section: string | null
  out_of_scope: boolean
  conflict_detected: boolean
  conflict_statement: string | null
}

export interface EvalClarifyResponse {
  kind: 'clarifying_question'
  question: string
  options: string[]
}

export type EvalResponse = EvalAnswerResponse | EvalClarifyResponse

export interface EvalUserTurn { role: 'user'; content: string }
export interface EvalAssistantTurn { role: 'assistant'; response: EvalResponse }
export type EvalTurn = EvalUserTurn | EvalAssistantTurn

export interface EvalDeterministicMetric {
  name: string
  label: string
  reason: string
}

export interface EvalJudgeRubric {
  name: string
  score: number | null
  label: string | null
  reason: string
  applicable: boolean
}

export interface EvalRecordExpected {
  passage_ids: string[]
  out_of_scope: boolean
  general_knowledge: boolean
  conflict_mention: boolean
  must_cite_at_least: number
}

export interface EvalRecord {
  id: string
  bucket: string
  language: 'pt' | 'en' | 'es'
  question: string
  expected: EvalRecordExpected
  duration_ms: number
  turns: EvalTurn[]
  deterministic: EvalDeterministicMetric[]
  judge: EvalJudgeRubric[]
}

export interface EvalMockMeta {
  run_dir: string
  combined_basename: string
  judge_basename: string
  judge_model: string
  judge_prompt_hash: string
  agent_model: string
  reasoning_effort: string
  question_count: number
}
'''
    meta_json = json.dumps(meta, ensure_ascii=False, indent=2)
    records_json = json.dumps(records, ensure_ascii=False, indent=2)
    return (
        header
        + f"\nexport const EVAL_MOCK_META: EvalMockMeta = {meta_json}\n\n"
        + f"export const EVAL_MOCK: EvalRecord[] = {records_json}\n"
    )


def main() -> None:
    if not COMBINED_CSV.exists():
        raise SystemExit(f"missing: {COMBINED_CSV}")
    if not JUDGE_FILE.exists():
        raise SystemExit(f"missing: {JUDGE_FILE}")

    det_by_id = load_det_metrics()
    judge_by_id = load_judge()
    traces = latest_trace_per_question()

    records: list[dict] = []
    for qid in sorted(traces.keys(), key=lambda s: int(s.lstrip("q"))):
        with open(traces[qid], encoding="utf-8") as f:
            trace = json.loads(f.readline())
        det = det_by_id.get(qid, [])
        judge = judge_by_id.get(qid, [])
        records.append(build_record(trace, det, judge))

    meta = {
        "run_dir": "evals/results/0007",
        "combined_basename": COMBINED_CSV.name,
        "judge_basename": "judge/all_judges.jsonl",
        "judge_model": "claude-opus-4-7",
        "judge_prompt_hash": "0f42c967",
        "agent_model": "gpt-5.5",
        "reasoning_effort": "low",
        "question_count": len(records),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(emit_ts(records, meta), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({len(records)} records, {size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
