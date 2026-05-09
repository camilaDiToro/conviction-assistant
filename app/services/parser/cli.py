"""CLI: print parser stats for a convictions directory.

Usage:
    uv run python -m app.services.parser.cli convictions/

Dev convenience for inspecting parser output without spinning up the API.
"""

import sys
from pathlib import Path

from app.services.parser import parse_corpus


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m app.services.parser.cli <convictions_dir>", file=sys.stderr)
        return 1

    directory = Path(argv[1])
    if not directory.is_dir():
        print(f"not a directory: {directory}", file=sys.stderr)
        return 1

    passages = parse_corpus(directory)
    if not passages:
        print(f"no passages found under {directory}")
        return 0

    doc_dates = {p.document_id: p.document_updated for p in passages}
    dated = sum(1 for d in doc_dates.values() if d is not None)
    undated_docs = sorted(d for d, dt in doc_dates.items() if dt is None)
    longest = sorted(passages, key=lambda p: len(p.text), reverse=True)[:5]

    print(f"documents:           {len(doc_dates)}")
    print(f"  dated:             {dated}")
    print(f"  undated:           {len(undated_docs)}")
    print(f"passages:            {len(passages)}")
    print()
    print("undated documents:")
    for d in undated_docs:
        print(f"  - {d}")
    print()
    print("top-5 longest passages:")
    for p in longest:
        print(f"  - {p.id}  ({len(p.text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
