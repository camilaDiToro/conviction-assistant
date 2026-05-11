"""Diff two eval run CSVs.

Usage:

    uv run python -m evals.compare evals/results/run_a.csv evals/results/run_b.csv

Emits a markdown report:
- Aggregate metric deltas (anchor_rate, cost, etc.)
- Questions that regressed (passed in A, failing in B)
- Questions that improved (failing in A, passing in B)
- Per-bucket anchor-rate comparison
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from evals.report import aggregate


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def _pass(row: pd.Series) -> bool:
    """A question 'passes' when:
    - it cited at least one passage AND every citation anchored (anchor_rate=1.0),
      OR
    - it correctly refused (refusal_correctness=='correct') and cited nothing.
    """
    if row.get("refusal_correctness") == "correct":
        return True
    citations = int(row.get("citations_count", 0) or 0)
    if citations == 0:
        return False
    return float(row.get("anchor_rate", 0) or 0) >= 1.0


def _diff_aggregate(a: dict, b: dict) -> str:
    md: list[str] = []
    md.append("## Aggregate delta")
    md.append("")
    md.append("| Metric | A | B | Δ |")
    md.append("|---|---|---|---|")
    fields = ("anchor_rate", "citation_precision", "cost_usd_total", "cost_usd_mean")
    for f in fields:
        va = a.get(f)
        vb = b.get(f)
        delta = (vb - va) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else "—"
        if isinstance(delta, float):
            delta = f"{delta:+.4f}"
        md.append(f"| {f} | {va} | {vb} | {delta} |")
    md.append("")
    return "\n".join(md)


def _diff_questions(a: pd.DataFrame, b: pd.DataFrame) -> tuple[list[str], list[str]]:
    merged = pd.merge(
        a[["id", "bucket", "anchor_rate", "citations_count", "refusal_correctness", "cost_usd"]],
        b[["id", "bucket", "anchor_rate", "citations_count", "refusal_correctness", "cost_usd"]],
        on="id",
        how="outer",
        suffixes=("_a", "_b"),
    )
    regressions: list[str] = []
    improvements: list[str] = []
    for _, row in merged.iterrows():
        # Some rows may be missing in one side; treat as fail.
        row_a = {
            "anchor_rate": row.get("anchor_rate_a"),
            "citations_count": row.get("citations_count_a"),
            "refusal_correctness": row.get("refusal_correctness_a"),
        }
        row_b = {
            "anchor_rate": row.get("anchor_rate_b"),
            "citations_count": row.get("citations_count_b"),
            "refusal_correctness": row.get("refusal_correctness_b"),
        }
        passed_a = _pass(pd.Series(row_a))
        passed_b = _pass(pd.Series(row_b))
        if passed_a and not passed_b:
            regressions.append(
                f"- **{row['id']}** ({row.get('bucket_a') or row.get('bucket_b')}): "
                f"anchor {row.get('anchor_rate_a')} → {row.get('anchor_rate_b')}"
            )
        elif not passed_a and passed_b:
            improvements.append(
                f"- **{row['id']}** ({row.get('bucket_a') or row.get('bucket_b')}): "
                f"anchor {row.get('anchor_rate_a')} → {row.get('anchor_rate_b')}"
            )
    return regressions, improvements


def _diff_per_bucket(a: dict, b: dict) -> str:
    md: list[str] = []
    md.append("## Per-bucket anchor rate")
    md.append("")
    md.append("| Bucket | A (n) | A rate | B (n) | B rate | Δ |")
    md.append("|---|---|---|---|---|---|")
    buckets = sorted(set(a.get("by_bucket", {}).keys()) | set(b.get("by_bucket", {}).keys()))
    for bucket in buckets:
        ba = a.get("by_bucket", {}).get(bucket, {})
        bb = b.get("by_bucket", {}).get(bucket, {})
        ar = ba.get("anchor_rate")
        br = bb.get("anchor_rate")
        delta = (br - ar) if isinstance(ar, (int, float)) and isinstance(br, (int, float)) else "—"
        if isinstance(delta, float):
            delta = f"{delta:+.4f}"
        md.append(f"| {bucket} | {ba.get('n', 0)} | {ar} | {bb.get('n', 0)} | {br} | {delta} |")
    md.append("")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("a", type=Path, help="baseline run CSV")
    parser.add_argument("b", type=Path, help="new run CSV")
    parser.add_argument("--out", type=Path, default=None, help="write markdown to file")
    args = parser.parse_args()

    a = _load(args.a)
    b = _load(args.b)
    agg_a = aggregate(a)
    agg_b = aggregate(b)

    md: list[str] = []
    md.append(f"# Eval comparison — {args.a.name} vs {args.b.name}")
    md.append("")
    md.append(_diff_aggregate(agg_a, agg_b))
    regressions, improvements = _diff_questions(a, b)
    md.append("## Regressions (passed in A, failing in B)")
    md.append("")
    md.append("\n".join(regressions) if regressions else "_None._")
    md.append("")
    md.append("## Improvements (failing in A, passing in B)")
    md.append("")
    md.append("\n".join(improvements) if improvements else "_None._")
    md.append("")
    md.append(_diff_per_bucket(agg_a, agg_b))

    output = "\n".join(md) + "\n"
    if args.out:
        args.out.write_text(output, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
