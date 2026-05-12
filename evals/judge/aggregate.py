"""Combined deterministic + judge report.

CLI:

    uv run python -m evals.judge.aggregate \
        evals/results/<ts>_..._.csv \
        evals/results/<ts>_..._judge.jsonl \
        [--out combined.md]

Merges the deterministic per-question DataFrame with the judge JSONL
on ``id``, then writes a markdown report with five sections:

1. Run signatures (agent model + reasoning, judge model + prompt hash).
2. Deterministic aggregate (existing + new metrics).
3. Judge aggregate (mean score per metric, overall + per-bucket).
4. Per-question table (id / bucket / anchor / precision / faithfulness /
   attribution / completeness).
5. Worst offenders — questions where deterministic passed but the judge
   flagged the answer (anchored-but-unfaithful and similar).

The aggregator refuses to merge a judge JSONL whose records carry
inconsistent ``(judge_model, judge_prompt_hash)`` — that's the
cross-model comparison contract.
"""

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from evals.judge.loader import load_judge_results
from evals.judge.schema import METRIC_NAMES, JudgeResult


@dataclass(frozen=True, slots=True)
class _JudgeSignature:
    judge_model: str
    judge_prompt_hash: str


def _check_signature(results: list[JudgeResult]) -> _JudgeSignature:
    if not results:
        raise ValueError("judge JSONL is empty")
    sigs = {(r.judge_model, r.judge_prompt_hash) for r in results}
    if len(sigs) > 1:
        raise ValueError(
            f"judge JSONL mixes multiple (judge_model, judge_prompt_hash) "
            f"signatures: {sorted(sigs)} — cannot aggregate"
        )
    model, prompt_hash = sigs.pop()
    return _JudgeSignature(judge_model=model, judge_prompt_hash=prompt_hash)


def _judge_frame(results: list[JudgeResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        row = {"id": r.id, **r.metric_scores()}
        rows.append(row)
    return pd.DataFrame(rows)


def _judge_aggregate(judge_df: pd.DataFrame) -> dict[str, float | None]:
    """Mean of non-null scores per metric across the whole run."""
    out: dict[str, float | None] = {}
    for metric in METRIC_NAMES:
        col = judge_df[metric].dropna()
        out[metric] = round(float(col.mean()), 4) if len(col) else None
    return out


def _judge_by_bucket(merged: pd.DataFrame) -> dict[str, dict[str, float | None]]:
    by_bucket: dict[str, dict[str, float | None]] = {}
    for bucket, sub in merged.groupby("bucket"):
        bucket_str = str(bucket)
        scores: dict[str, float | None] = {"n": int(len(sub))}
        for metric in METRIC_NAMES:
            col = sub[metric].dropna()
            scores[metric] = round(float(col.mean()), 4) if len(col) else None
        by_bucket[bucket_str] = scores
    return by_bucket


def _worst_offenders(merged: pd.DataFrame) -> list[dict[str, object]]:
    """Questions where the deterministic anchor_rate is high (>=1.0) but a
    judge metric flagged real failure (faithfulness < 0.7, or rule_a_purity
    leaked, or citation_attribution < 0.7).
    """
    offenders: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        anchor = float(row.get("anchor_rate") or 0)
        faith = row.get("faithfulness")
        attr = row.get("citation_attribution")
        purity = row.get("rule_a_purity")
        flagged: list[str] = []
        if anchor >= 1.0 and faith is not None and faith < 0.7:
            flagged.append(f"faithfulness={faith:.2f}")
        if anchor >= 1.0 and attr is not None and attr < 0.7:
            flagged.append(f"attribution={attr:.2f}")
        if purity is not None and purity == 0.0:
            flagged.append("rule_a_purity=leaked")
        if flagged:
            offenders.append(
                {
                    "id": row["id"],
                    "bucket": row["bucket"],
                    "anchor_rate": anchor,
                    "flagged": ", ".join(flagged),
                }
            )
    return offenders


def _load_det_metadata(det_csv: Path) -> dict[str, object]:
    sibling = det_csv.with_suffix(".json")
    if not sibling.exists():
        return {}
    try:
        payload = json.loads(sibling.read_text(encoding="utf-8"))
        return payload.get("run_metadata", {}) if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.3f}"


def _render(
    *,
    det_metadata: dict[str, object],
    judge_signature: _JudgeSignature,
    det_df: pd.DataFrame,
    merged: pd.DataFrame,
    judge_agg: dict[str, float | None],
    judge_by_bucket: dict[str, dict[str, float | None]],
    offenders: Iterable[dict[str, object]],
) -> str:
    md: list[str] = []
    md.append("# Combined eval report — deterministic + LLM-as-judge")
    md.append("")

    md.append("## Run signatures")
    md.append("")
    md.append("| Field | Value |")
    md.append("|---|---|")
    for k in (
        "timestamp",
        "model",
        "reasoning_effort",
        "rewrite_reasoning_effort",
        "agent_max_tool_calls",
        "prompt_version",
        "git_sha",
        "subset",
    ):
        md.append(f"| det.{k} | `{det_metadata.get(k)}` |")
    md.append(f"| judge_model | `{judge_signature.judge_model}` |")
    md.append(f"| judge_prompt_hash | `{judge_signature.judge_prompt_hash}` |")
    md.append(f"| questions (det) | {len(det_df)} |")
    md.append(f"| questions (merged) | {len(merged)} |")
    md.append("")

    md.append("## Judge aggregate")
    md.append("")
    md.append("| Metric | Score |")
    md.append("|---|---|")
    for metric in METRIC_NAMES:
        md.append(f"| {metric} | {_fmt(judge_agg.get(metric))} |")
    md.append("")

    md.append("## Judge per-bucket")
    md.append("")
    md.append(
        "| Bucket | N | faithfulness | answer_relevancy | "
        "rule_a_purity | citation_attribution | completeness |"
    )
    md.append("|---|---|---|---|---|---|---|")
    for bucket in sorted(judge_by_bucket):
        b = judge_by_bucket[bucket]
        md.append(
            "| "
            + " | ".join(
                [
                    bucket,
                    str(b["n"]),
                    _fmt(b.get("faithfulness")),
                    _fmt(b.get("answer_relevancy")),
                    _fmt(b.get("rule_a_purity")),
                    _fmt(b.get("citation_attribution")),
                    _fmt(b.get("completeness")),
                ]
            )
            + " |"
        )
    md.append("")

    md.append("## Per-question (deterministic + judge)")
    md.append("")
    md.append(
        "| id | bucket | anchor | prec | recall | faithfulness | attribution | completeness |"
    )
    md.append("|---|---|---|---|---|---|---|---|")
    for _, row in merged.iterrows():
        md.append(
            "| "
            + " | ".join(
                [
                    str(row["id"]),
                    str(row["bucket"]),
                    _fmt(float(row["anchor_rate"]) if row["anchor_rate"] is not None else None),
                    _fmt(
                        float(row["citation_precision"])
                        if row["citation_precision"] is not None
                        else None
                    ),
                    _fmt(
                        float(row["citation_recall"])
                        if row["citation_recall"] is not None
                        else None
                    ),
                    _fmt(row.get("faithfulness")),
                    _fmt(row.get("citation_attribution")),
                    _fmt(row.get("completeness")),
                ]
            )
            + " |"
        )
    md.append("")

    md.append("## Worst offenders (deterministic passed, judge flagged)")
    md.append("")
    offenders = list(offenders)
    if not offenders:
        md.append("_None — every anchored answer also passed the judge thresholds._")
    else:
        md.append("| id | bucket | anchor | flagged |")
        md.append("|---|---|---|---|")
        for o in offenders:
            anchor = o["anchor_rate"]
            anchor_str = _fmt(anchor) if isinstance(anchor, (int, float)) else "—"
            md.append(f"| {o['id']} | {o['bucket']} | {anchor_str} | {o['flagged']} |")
    md.append("")
    return "\n".join(md) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("det_csv", type=Path, help="deterministic run CSV (the source of truth)")
    parser.add_argument("judge_jsonl", type=Path, help="judge run JSONL (one JudgeResult per line)")
    parser.add_argument("--out", type=Path, default=None, help="write markdown to file")
    args = parser.parse_args()

    det_df = pd.read_csv(args.det_csv)
    judge_results = load_judge_results(args.judge_jsonl)
    signature = _check_signature(judge_results)
    judge_df = _judge_frame(judge_results)
    merged = pd.merge(det_df, judge_df, on="id", how="inner")
    if merged.empty:
        raise SystemExit(
            f"no overlapping ids between {args.det_csv.name} and {args.judge_jsonl.name}"
        )

    det_metadata = _load_det_metadata(args.det_csv)
    judge_agg = _judge_aggregate(judge_df)
    judge_by_bucket = _judge_by_bucket(merged)
    offenders = _worst_offenders(merged)

    body = _render(
        det_metadata=det_metadata,
        judge_signature=signature,
        det_df=det_df,
        merged=merged,
        judge_agg=judge_agg,
        judge_by_bucket=judge_by_bucket,
        offenders=offenders,
    )

    if args.out:
        args.out.write_text(body, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
