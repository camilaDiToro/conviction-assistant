"""Histogram of passage lengths (characters + words). Throwaway.

Usage:
    uv run python scripts/_passage_length_histogram.py
    uv run python scripts/_passage_length_histogram.py --bins 30 --metric words
    uv run python scripts/_passage_length_histogram.py --png out.png

Reads passages.text directly from the SQLite DB at data/conviction_assistant.sqlite.
Always prints an ASCII histogram. If matplotlib is installed, also writes a PNG.
"""

import argparse
import sqlite3
import statistics
from pathlib import Path

DEFAULT_DB = Path("data/conviction_assistant.sqlite")


def fetch_lengths(db: Path, metric: str) -> list[int]:
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT text FROM passages").fetchall()
    finally:
        con.close()
    if metric == "chars":
        return [len(r[0]) for r in rows]
    if metric == "words":
        return [len(r[0].split()) for r in rows]
    raise ValueError(f"unknown metric: {metric}")


def ascii_histogram(values: list[int], bins: int, width: int = 60) -> str:
    if not values:
        return "(no passages)"
    lo, hi = min(values), max(values)
    if lo == hi:
        return f"all values = {lo} (n={len(values)})"
    step = (hi - lo) / bins
    edges = [lo + i * step for i in range(bins + 1)]
    counts = [0] * bins
    for v in values:
        idx = min(int((v - lo) / step), bins - 1)
        counts[idx] += 1
    peak = max(counts) or 1
    lines = []
    for i, c in enumerate(counts):
        bar = "#" * int(c / peak * width)
        lines.append(f"{edges[i]:7.0f} - {edges[i + 1]:7.0f} | {c:5d} {bar}")
    return "\n".join(lines)


def summary(values: list[int]) -> str:
    if not values:
        return "n=0"
    qs = statistics.quantiles(values, n=4) if len(values) > 1 else [values[0]] * 3
    return (
        f"n={len(values)}  min={min(values)}  p25={qs[0]:.0f}  "
        f"median={statistics.median(values):.0f}  p75={qs[2]:.0f}  "
        f"max={max(values)}  mean={statistics.fmean(values):.1f}"
    )


def maybe_save_png(values: list[int], bins: int, metric: str, path: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return False

    arr = np.array(values)
    median = float(np.median(arr))
    p75 = float(np.percentile(arr, 75))
    p95 = float(np.percentile(arr, 95))
    p99 = float(np.percentile(arr, 99))

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))

    # Panel 1: full range, log-y so the long tail is still readable.
    ax1.hist(arr, bins=bins, edgecolor="black", color="#4C78A8")
    ax1.set_yscale("log")
    ax1.set_xlabel(f"length ({metric})")
    ax1.set_ylabel("count (log)")
    ax1.set_title("Full range, log-y")

    # Panel 2: log-x so the body and the tail share the screen fairly.
    pos = arr[arr > 0]
    log_bins = np.logspace(np.log10(pos.min()), np.log10(pos.max()), bins)
    ax2.hist(pos, bins=log_bins, edgecolor="black", color="#54A24B")
    ax2.set_xscale("log")
    ax2.set_xlabel(f"length ({metric}, log)")
    ax2.set_ylabel("count")
    ax2.set_title("Log-x: spread across orders of magnitude")

    # Panel 3: zoom to p99 — that's where 99% of the mass actually lives.
    body = arr[arr <= p99]
    ax3.hist(body, bins=bins, edgecolor="black", color="#E45756")
    for x, lbl, c in [(median, "median", "black"), (p75, "p75", "#444"), (p95, "p95", "#888")]:
        ax3.axvline(x, color=c, linestyle="--", linewidth=1)
        ax3.text(x, ax3.get_ylim()[1] * 0.95, f" {lbl}={x:.0f}", rotation=90,
                 va="top", ha="left", fontsize=8)
    ax3.set_xlabel(f"length ({metric}), clipped at p99={p99:.0f}")
    ax3.set_ylabel("count")
    ax3.set_title("Zoomed to p99 (body of the distribution)")

    fig.suptitle(f"Passage length distribution ({metric}, n={len(values)})", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--metric", choices=["chars", "words"], default="chars")
    ap.add_argument("--bins", type=int, default=25)
    ap.add_argument("--png", type=Path, default=Path("passage_length_hist.png"))
    args = ap.parse_args()

    if not args.db.exists():
        raise SystemExit(f"DB not found at {args.db}. Run ingest first.")

    values = fetch_lengths(args.db, args.metric)
    print(f"metric: {args.metric}")
    print(summary(values))
    print()
    print(ascii_histogram(values, args.bins))

    if maybe_save_png(values, args.bins, args.metric, args.png):
        print(f"\nPNG saved: {args.png}")
    else:
        print("\n(matplotlib not installed — skipping PNG. `uv pip install matplotlib` to enable.)")


if __name__ == "__main__":
    main()
