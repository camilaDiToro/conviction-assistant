"""Dump traces for judge inspection. Throwaway."""

import json
import sys
from pathlib import Path


def main(paths: list[str]) -> None:
    for path in paths:
        p = Path(path)
        print(f"=== {p.name}")
        with p.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                print(f"--- {r['id']} {r['bucket']} {r['language']}")
                print(f"QUESTION: {r['question']}")
                print(f"EXPECTED_PASSAGE_IDS: {r.get('expected_passage_ids')}")
                print(f"EXPECTED_CONFLICT: {r.get('expected_conflict_mention')}")
                print(f"EXPECTED_GEN_KNOW: {r.get('expected_general_knowledge')}")
                print(f"EXPECTED_OUT_OF_SCOPE: {r.get('expected_out_of_scope')}")
                print(f"MUST_CITE_AT_LEAST: {r.get('must_cite_at_least')}")
                result = r.get("result") or {}
                out = result.get("output") or {}
                print(f"KIND: {out.get('kind')}")
                print(f"OUT_OF_SCOPE: {out.get('out_of_scope')}")
                print(f"GEN_KNOW_USED: {out.get('general_knowledge_used')}")
                ans = out.get("answer")
                if ans:
                    print("ANSWER:")
                    print(ans)
                cl = out.get("question")
                if cl:
                    print(f"CLARIFY: {cl}")
                gks = out.get("general_knowledge_section")
                if gks:
                    print("GEN_KNOW_SECTION:")
                    print(gks)
                entries = (result.get("resolution") or {}).get("entries") or []
                print(f"CITATIONS: {len(entries)}")
                for i, e in enumerate(entries, 1):
                    print(
                        f"  [{i}] {e.get('passage_id')} "
                        f"anchored={e.get('failure_reason') is None}"
                    )
                    print(f"      TEXT: {(e.get('passage_text') or '')[:1200]}")
                print()


if __name__ == "__main__":
    main(sys.argv[1:])
