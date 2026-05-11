"""Render eval-run artefacts (CSV, JSON, Markdown).

The CSV is the source of truth (per-question rows; ``evals.compare``
diffs two of these). The JSON carries run metadata + aggregates so a
report can be reproduced without re-reading the CSV. The Markdown is
embeddable into the README.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class RunMetadata:
    timestamp: str
    provider: str
    model: str
    reasoning_effort: str
    rewrite_reasoning_effort: str
    agent_max_tool_calls: int
    agent_max_output_tokens: int
    git_sha: str | None
    subset: str  # e.g. "full", "limit5", "bucket-rule_b"
    with_judge: bool
    prompt_version: str = "unknown"
    openai_timeout_seconds: int | None = None


_REQUIRED_COLUMNS = (
    "id",
    "bucket",
    "language",
    "anchor_rate",
    "citation_precision",
    "refusal_correctness",
    "general_knowledge_correctness",
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "reasoning_tokens",
    "tool_calls",
    "duration_ms",
)


def aggregate(df: pd.DataFrame) -> dict[str, Any]:
    """Compute aggregate metrics from a per-question DataFrame.

    Strategy:

    - ``anchor_rate`` / ``citation_precision`` are weighted by the number
      of *applicable* questions (those with at least one citation, or
      with declared expected_passage_ids respectively).
    - Refusal / general-knowledge correctness are reported as
      correct-rate over questions where the metric was not 'n/a'.
    - Token usage / tool_calls / duration are summarised as mean and p95.
    """
    out: dict[str, Any] = {
        "questions": int(len(df)),
    }

    citing = df[df["anchor_rate"].notna() & (df["citations_count"] > 0)]
    out["anchor_rate"] = round(float(citing["anchor_rate"].mean()), 4) if len(citing) else None
    out["anchor_rate_n"] = int(len(citing))

    scored_precision = df[df["citation_precision"].notna() & (df["expected_passage_ids_count"] > 0)]
    out["citation_precision"] = (
        round(float(scored_precision["citation_precision"].mean()), 4)
        if len(scored_precision)
        else None
    )
    out["citation_precision_n"] = int(len(scored_precision))

    out["refusal_correctness"] = _discrete_rate(df["refusal_correctness"])
    out["general_knowledge_correctness"] = _discrete_rate(df["general_knowledge_correctness"])

    total_tokens = df["prompt_tokens"].fillna(0) + df["completion_tokens"].fillna(0)
    out["tokens_total"] = int(total_tokens.sum())
    out["tokens_mean"] = round(float(total_tokens.mean()), 2) if len(df) else 0
    out["tokens_p95"] = int(total_tokens.quantile(0.95)) if len(df) else 0
    out["prompt_tokens_total"] = int(df["prompt_tokens"].fillna(0).sum())
    out["completion_tokens_total"] = int(df["completion_tokens"].fillna(0).sum())
    out["cached_tokens_total"] = int(df["cached_tokens"].fillna(0).sum())
    out["reasoning_tokens_total"] = int(df["reasoning_tokens"].fillna(0).sum())

    out["tool_calls_mean"] = round(float(df["tool_calls"].mean()), 2)
    out["duration_ms_mean"] = int(df["duration_ms"].mean()) if len(df) else 0
    out["duration_ms_p95"] = int(df["duration_ms"].quantile(0.95)) if len(df) else 0

    by_bucket: dict[str, dict[str, Any]] = {}
    for bucket, sub in df.groupby("bucket"):
        citing_sub = sub[sub["citations_count"] > 0]
        by_bucket[str(bucket)] = {
            "n": int(len(sub)),
            "anchor_rate": (
                round(float(citing_sub["anchor_rate"].mean()), 4) if len(citing_sub) else None
            ),
            "tokens_mean": round(
                float((sub["prompt_tokens"].fillna(0) + sub["completion_tokens"].fillna(0)).mean()),
                2,
            ),
        }
    out["by_bucket"] = by_bucket
    return out


def _discrete_rate(series: pd.Series) -> dict[str, Any]:
    counts = series.value_counts(dropna=False).to_dict()
    correct = int(counts.get("correct", 0))
    incorrect = int(counts.get("incorrect", 0))
    na = int(counts.get("n/a", 0))
    scored = correct + incorrect
    return {
        "correct": correct,
        "incorrect": incorrect,
        "n/a": na,
        "rate": round(correct / scored, 4) if scored else None,
    }


def write_run(
    *,
    df: pd.DataFrame,
    metadata: RunMetadata,
    out_dir: Path,
    stem: str,
) -> tuple[Path, Path, Path]:
    """Write CSV, JSON, and Markdown for one eval run."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for col in _REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"DataFrame missing required column {col!r}")
    csv_path = out_dir / f"{stem}.csv"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    df.to_csv(csv_path, index=False)
    agg = aggregate(df)
    json_payload = {
        "run_metadata": asdict(metadata),
        "aggregate": agg,
    }
    json_path.write_text(json.dumps(json_payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(_render_markdown(metadata, df, agg), encoding="utf-8")
    return csv_path, json_path, md_path


def _render_markdown(metadata: RunMetadata, df: pd.DataFrame, agg: dict[str, Any]) -> str:
    md: list[str] = []
    md.append(f"# Eval run — {metadata.timestamp}")
    md.append("")
    md.append("## Run metadata")
    md.append("")
    md.append("| Field | Value |")
    md.append("|---|---|")
    for k, v in asdict(metadata).items():
        md.append(f"| {k} | `{v}` |")
    md.append("")

    md.append("## Aggregate")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|---|---|")
    md.append(f"| Questions evaluated | {agg['questions']} |")
    md.append(
        f"| Anchor rate (headline) | {_fmt(agg['anchor_rate'])} "
        f"(across {agg['anchor_rate_n']} citing questions) |"
    )
    md.append(
        f"| Citation precision | {_fmt(agg['citation_precision'])} "
        f"(across {agg['citation_precision_n']} questions with expected ids) |"
    )
    refusal = agg["refusal_correctness"]
    refusal_scored = refusal["correct"] + refusal["incorrect"]
    md.append(
        f"| Refusal correctness | {_fmt_rate(refusal)} ({refusal['correct']}/{refusal_scored}) |"
    )
    gen_know = agg["general_knowledge_correctness"]
    gen_know_scored = gen_know["correct"] + gen_know["incorrect"]
    md.append(
        f"| General-knowledge correctness | {_fmt_rate(gen_know)} "
        f"({gen_know['correct']}/{gen_know_scored}) |"
    )
    md.append(f"| Tokens total | {agg['tokens_total']} |")
    md.append(f"| Tokens mean / p95 | {agg['tokens_mean']:.2f} / {agg['tokens_p95']} |")
    md.append(
        f"| Prompt / completion tokens | "
        f"{agg['prompt_tokens_total']} / {agg['completion_tokens_total']} |"
    )
    md.append(
        f"| Cached / reasoning tokens | "
        f"{agg['cached_tokens_total']} / {agg['reasoning_tokens_total']} |"
    )
    md.append(f"| Tool calls (mean) | {agg['tool_calls_mean']:.2f} |")
    md.append(f"| Duration mean / p95 | {agg['duration_ms_mean']}ms / {agg['duration_ms_p95']}ms |")
    md.append("")

    md.append("## Per-bucket anchor rate")
    md.append("")
    md.append("| Bucket | N | Anchor rate | Tokens mean |")
    md.append("|---|---|---|---|")
    for bucket, info in sorted(agg["by_bucket"].items()):
        rate = _fmt(info["anchor_rate"])
        tokens = f"{info['tokens_mean']:.2f}"
        md.append(f"| {bucket} | {info['n']} | {rate} | {tokens} |")
    md.append("")

    md.append("## Per-question results")
    md.append("")
    md.append(
        "| id | bucket | lang | citations | anchor | precision | refusal "
        "| gen-know | tokens | tools | ms |"
    )
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for _, row in df.iterrows():
        md.append(
            "| "
            + " | ".join(
                [
                    str(row["id"]),
                    str(row["bucket"]),
                    str(row["language"]),
                    f"{int(row['citations_count'])} ({int(row['anchored_count'])} anch)",
                    _fmt(row["anchor_rate"]),
                    _fmt(row["citation_precision"]),
                    str(row["refusal_correctness"]),
                    str(row["general_knowledge_correctness"]),
                    str(int(row["prompt_tokens"]) + int(row["completion_tokens"])),
                    str(int(row["tool_calls"])),
                    str(int(row["duration_ms"])),
                ]
            )
            + " |"
        )
    md.append("")

    return "\n".join(md) + "\n"


def _fmt(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _fmt_rate(r: dict[str, Any]) -> str:
    if r["rate"] is None:
        return "—"
    return f"{r['rate']:.3f}"


def iter_required_columns() -> Iterable[str]:
    return _REQUIRED_COLUMNS


__all__ = ["RunMetadata", "aggregate", "write_run", "iter_required_columns"]
