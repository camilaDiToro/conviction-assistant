"""Bundle the latest eval run (0009) into a TS file consumed by the design site.

Reads three sources from evals/results/0009/:
  - 2026-05-12_15-41-28_combined_openai_gpt-5.5_low.csv  (deterministic metrics)
  - per-question *_id-qNN_traces.jsonl                    (Q&A + resolved citations)
  - judge/all_judges.jsonl                                (LLM-as-judge rubrics)

Emits frontend/src/data/eval_mock.ts with EVAL_MOCK[] + EVAL_MOCK_META.
"""

import csv
import glob
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "0009"
RUN_DIR = REPO_ROOT / "evals" / "results" / RUN_ID
COMBINED_CSV = RUN_DIR / "2026-05-12_15-41-28_combined_openai_gpt-5.5_low.csv"
RUN_JSON = COMBINED_CSV.with_suffix(".json")
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
    "conflict_disclosure_det",
    "language_match",
]

JUDGE_RUBRICS = [
    "faithfulness",
    "answer_relevancy",
    "rule_a_purity",
    "citation_attribution",
    "completeness",
]


def qid_sort_key(qid: str) -> int:
    return int(qid.lstrip("q"))


def to_int(value: str | None) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def to_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt_numeric(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}"


def fmt_metric_label(label: str) -> str:
    if not label:
        return "—"
    value = to_float(label)
    if value is not None:
        return fmt_numeric(value)
    return label


def fmt_int(value: int | float) -> str:
    return f"{int(value):,}"


def fmt_rate(rate_obj: dict) -> str:
    rate = rate_obj.get("rate")
    correct = int(rate_obj.get("correct") or 0)
    incorrect = int(rate_obj.get("incorrect") or 0)
    scored = correct + incorrect
    return f"{fmt_numeric(rate)} ({correct}/{scored})"


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


def load_det_rows() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(COMBINED_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[row["id"]] = row
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
                applicable = (
                    bool(r.get("applicable", True))
                    if "applicable" in r
                    else r.get("label") != "n/a"
                )
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


def build_det_metrics(row: dict) -> list[dict]:
    metrics = []
    for name in DET_METRICS:
        label = row.get(name, "") or ""
        reason = row.get(f"{name}_reason", "") or ""
        metrics.append({"name": name, "label": label, "reason": reason})
    return metrics


def build_stats(row: dict) -> dict:
    return {
        "expected_passage_ids_count": to_int(row.get("expected_passage_ids_count")),
        "citations_count": to_int(row.get("citations_count")),
        "anchored_count": to_int(row.get("anchored_count")),
        "prompt_tokens": to_int(row.get("prompt_tokens")),
        "completion_tokens": to_int(row.get("completion_tokens")),
        "cached_tokens": to_int(row.get("cached_tokens")),
        "reasoning_tokens": to_int(row.get("reasoning_tokens")),
        "tool_calls": to_int(row.get("tool_calls")),
    }


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
        if pt["role"] == "assistant":
            turns.append(
                {
                    "role": "assistant",
                    "response": {
                        "kind": "answer",
                        "answer": pt.get("content", ""),
                        "citations": [],
                        "general_knowledge_used": False,
                        "general_knowledge_section": None,
                        "out_of_scope": False,
                        "conflict_detected": False,
                        "conflict_statement": None,
                    },
                }
            )
        else:
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


def build_record(trace: dict, det_row: dict, judge: list[dict]) -> dict:
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
        "stats": build_stats(det_row),
        "turns": build_turns(trace, citations),
        "deterministic": build_det_metrics(det_row),
        "judge": judge,
    }


def load_run_payload() -> dict:
    with open(RUN_JSON, encoding="utf-8") as f:
        return json.load(f)


def build_run_meta_rows(payload: dict) -> list[list[str]]:
    meta = payload["run_metadata"]
    return [
        ["timestamp", str(meta["timestamp"])],
        ["provider", str(meta["provider"])],
        ["model", str(meta["model"])],
        ["reasoning_effort", str(meta["reasoning_effort"])],
        ["rewrite_reasoning_effort", str(meta.get("rewrite_reasoning_effort", "low"))],
        ["agent_max_tool_calls", str(meta["agent_max_tool_calls"])],
        ["agent_max_output_tokens", str(meta["agent_max_output_tokens"])],
        ["git_sha", str(meta.get("git_sha") or "unknown")],
        ["subset", str(meta["subset"])],
        ["prompt_version", str(meta.get("prompt_version", "unknown"))],
    ]


def build_aggregate_rows(payload: dict) -> list[list[str]]:
    agg = payload["aggregate"]
    return [
        ["Questions evaluated", str(agg["questions"])],
        [
            "Anchor rate (headline)",
            f"{fmt_numeric(agg['anchor_rate'])} (across {agg['anchor_rate_n']} citing questions)",
        ],
        [
            "Citation precision",
            f"{fmt_numeric(agg['citation_precision'])} "
            f"(across {agg['citation_precision_n']} questions with expected ids)",
        ],
        [
            "Citation recall",
            f"{fmt_numeric(agg['citation_recall'])} "
            f"(across {agg['citation_recall_n']} questions with expected ids)",
        ],
        ["Refusal correctness", fmt_rate(agg["refusal_correctness"])],
        ["General-knowledge correctness", fmt_rate(agg["general_knowledge_correctness"])],
        ["Clarify correctness", fmt_rate(agg["clarify_correctness"])],
        ["Meets min citations", fmt_rate(agg["meets_min_citations"])],
        ["Conflict min citations (Rule B precondition)", fmt_rate(agg["conflict_min_citations"])],
        ["Conflict disclosure (Rule B semantic)", fmt_rate(agg["conflict_disclosure_det"])],
        ["Language match", fmt_rate(agg["language_match"])],
        ["Tokens total", fmt_int(agg["tokens_total"])],
        ["Tokens mean / p95", f"{agg['tokens_mean']:.2f} / {fmt_int(agg['tokens_p95'])}"],
        [
            "Prompt / completion tokens",
            f"{fmt_int(agg['prompt_tokens_total'])} / {fmt_int(agg['completion_tokens_total'])}",
        ],
        [
            "Cached / reasoning tokens",
            f"{fmt_int(agg['cached_tokens_total'])} / {fmt_int(agg['reasoning_tokens_total'])}",
        ],
        ["Tool calls (mean)", f"{agg['tool_calls_mean']:.2f}"],
        [
            "Duration mean / p95",
            f"{fmt_int(agg['duration_ms_mean'])}ms / {fmt_int(agg['duration_ms_p95'])}ms",
        ],
    ]


def build_bucket_rows(payload: dict) -> list[dict]:
    rows = []
    for bucket, info in sorted(payload["aggregate"]["by_bucket"].items()):
        rows.append(
            {
                "bucket": bucket,
                "n": int(info["n"]),
                "anchor": fmt_numeric(info["anchor_rate"]),
                "tokens": f"{info['tokens_mean']:,.2f}",
            }
        )
    return rows


def find_metric(metrics: list[dict], name: str) -> str:
    for metric in metrics:
        if metric["name"] == name:
            return metric["label"] or ""
    return ""


def find_judge_score(judge: list[dict], name: str) -> float | None:
    for rubric in judge:
        if rubric["name"] == name:
            return rubric["score"]
    return None


def build_per_question_rows(records: list[dict]) -> list[dict]:
    rows = []
    for record in records:
        stats = record["stats"]
        deterministic = record["deterministic"]
        rows.append(
            {
                "id": record["id"],
                "bucket": record["bucket"],
                "lang": record["language"],
                "citations": f"{stats['citations_count']} ({stats['anchored_count']} anch)",
                "anchor": fmt_metric_label(find_metric(deterministic, "anchor_rate")),
                "prec": fmt_metric_label(find_metric(deterministic, "citation_precision")),
                "recall": fmt_metric_label(find_metric(deterministic, "citation_recall")),
                "refusal": fmt_metric_label(find_metric(deterministic, "refusal_correctness")),
                "genKnow": fmt_metric_label(
                    find_metric(deterministic, "general_knowledge_correctness")
                ),
                "conflict": fmt_metric_label(find_metric(deterministic, "conflict_disclosure_det")),
                "langMatch": fmt_metric_label(find_metric(deterministic, "language_match")),
                "faithfulness": fmt_numeric(find_judge_score(record["judge"], "faithfulness")),
                "attribution": fmt_numeric(
                    find_judge_score(record["judge"], "citation_attribution")
                ),
                "completeness": fmt_numeric(find_judge_score(record["judge"], "completeness")),
                "tools": stats["tool_calls"],
                "ms": record["duration_ms"],
            }
        )
    return rows


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def build_judge_aggregate_rows(records: list[dict]) -> list[list[str]]:
    rows = []
    for name in JUDGE_RUBRICS:
        scores = [
            rubric["score"]
            for record in records
            for rubric in record["judge"]
            if rubric["name"] == name and rubric["score"] is not None
        ]
        rows.append([name, fmt_numeric(average(scores))])
    return rows


def build_judge_bucket_rows(records: list[dict]) -> list[dict]:
    rows = []
    for bucket in sorted({record["bucket"] for record in records if record["judge"]}):
        bucket_records = [
            record for record in records if record["bucket"] == bucket and record["judge"]
        ]
        row = {"bucket": bucket, "n": len(bucket_records)}
        for name in JUDGE_RUBRICS:
            scores = [
                rubric["score"]
                for record in bucket_records
                for rubric in record["judge"]
                if rubric["name"] == name and rubric["score"] is not None
            ]
            row[name] = fmt_numeric(average(scores))
        rows.append(row)
    return rows


def emit_ts(records: list[dict], meta: dict) -> str:
    header = '''// AUTO-GENERATED by scripts/build_eval_mock.py — do not edit by hand.
// Source: evals/results/0009/ (deterministic + LLM-as-judge run).

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

export interface EvalRecordStats {
  expected_passage_ids_count: number
  citations_count: number
  anchored_count: number
  prompt_tokens: number
  completion_tokens: number
  cached_tokens: number
  reasoning_tokens: number
  tool_calls: number
}

export interface EvalRecord {
  id: string
  bucket: string
  language: 'pt' | 'en' | 'es'
  question: string
  expected: EvalRecordExpected
  duration_ms: number
  stats: EvalRecordStats
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
  judge_question_count: number
}

export interface EvalBucketResult {
  bucket: string
  n: number
  anchor: string
  tokens: string
}

export interface EvalPerQuestionResult {
  id: string
  bucket: string
  lang: string
  citations: string
  anchor: string
  prec: string
  recall: string
  refusal: string
  genKnow: string
  conflict: string
  langMatch: string
  faithfulness: string
  attribution: string
  completeness: string
  tools: number
  ms: number
}

export interface EvalJudgeBucketResult {
  bucket: string
  n: number
  faithfulness: string
  answer_relevancy: string
  rule_a_purity: string
  citation_attribution: string
  completeness: string
}
'''
    meta_json = json.dumps(meta, ensure_ascii=False, indent=2)
    records_json = json.dumps(records, ensure_ascii=False, indent=2)
    payload = load_run_payload()
    run_meta_rows_json = json.dumps(build_run_meta_rows(payload), ensure_ascii=False, indent=2)
    aggregate_json = json.dumps(build_aggregate_rows(payload), ensure_ascii=False, indent=2)
    buckets_json = json.dumps(build_bucket_rows(payload), ensure_ascii=False, indent=2)
    per_question_json = json.dumps(build_per_question_rows(records), ensure_ascii=False, indent=2)
    judge_aggregate_json = json.dumps(
        build_judge_aggregate_rows(records), ensure_ascii=False, indent=2
    )
    judge_buckets_json = json.dumps(build_judge_bucket_rows(records), ensure_ascii=False, indent=2)
    return (
        header
        + f"\nexport const EVAL_MOCK_META: EvalMockMeta = {meta_json}\n\n"
        + "export const EVAL_RUN_META_ROWS: ReadonlyArray<[string, string]> = "
        + f"{run_meta_rows_json}\n\n"
        + f"export const EVAL_AGGREGATE: ReadonlyArray<[string, string]> = {aggregate_json}\n\n"
        + f"export const EVAL_BUCKET_RESULTS: EvalBucketResult[] = {buckets_json}\n\n"
        + "export const EVAL_JUDGE_AGGREGATE: ReadonlyArray<[string, string]> = "
        + f"{judge_aggregate_json}\n\n"
        + "export const EVAL_JUDGE_BUCKET_RESULTS: EvalJudgeBucketResult[] = "
        + f"{judge_buckets_json}\n\n"
        + f"export const EVAL_PER_QUESTION: EvalPerQuestionResult[] = {per_question_json}\n\n"
        + f"export const EVAL_MOCK: EvalRecord[] = {records_json}\n"
    )


def main() -> None:
    if not COMBINED_CSV.exists():
        raise SystemExit(f"missing: {COMBINED_CSV}")
    if not RUN_JSON.exists():
        raise SystemExit(f"missing: {RUN_JSON}")
    if not JUDGE_FILE.exists():
        raise SystemExit(f"missing: {JUDGE_FILE}")

    det_by_id = load_det_rows()
    judge_by_id = load_judge()
    traces = latest_trace_per_question()

    records: list[dict] = []
    for qid in sorted(traces.keys(), key=qid_sort_key):
        with open(traces[qid], encoding="utf-8") as f:
            trace = json.loads(f.readline())
        det = det_by_id.get(qid)
        if det is None:
            raise SystemExit(f"missing deterministic row for {qid}")
        judge = judge_by_id.get(qid, [])
        records.append(build_record(trace, det, judge))

    meta = {
        "run_dir": f"evals/results/{RUN_ID}",
        "combined_basename": COMBINED_CSV.name,
        "judge_basename": "judge/all_judges.jsonl",
        "judge_model": "claude-opus-4-7",
        "judge_prompt_hash": "601a0bd7",
        "agent_model": "gpt-5.5",
        "reasoning_effort": "low",
        "question_count": len(records),
        "judge_question_count": sum(1 for record in records if record["judge"]),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(emit_ts(records, meta), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({len(records)} records, {size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
