"""Golden set loader.

The golden set is a hand-authored YAML list under ``evals/golden_set.yaml``.
This module turns it into typed ``Golden`` records that the runner consumes.

Schema (one entry per item):

```yaml
- id: q01
  question: "¿Qué dice Decade sobre CDBs y tributação?"
  language: pt                  # pt | en | es
  bucket: factual               # factual | rule_a | rule_b | cross_lang | out_of_scope | clarify
  expected_passage_ids: []      # optional; enables citation_precision
  must_cite_at_least: 1         # default 1; 0 for out_of_scope / clarify
  expected_out_of_scope: false
  expected_general_knowledge: false
  expected_conflict_mention: false
  prior_turns:                  # optional; multiturn setup before `question`
    - role: user                # role: "user" | "assistant"
      content: "..."
    - role: assistant
      content: "..."
  notes: "..."
```
"""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from app.i18n import SUPPORTED_LANGUAGES, Language

Bucket = Literal["factual", "rule_a", "rule_b", "cross_lang", "out_of_scope", "clarify"]

_VALID_BUCKETS: frozenset[str] = frozenset(
    {"factual", "rule_a", "rule_b", "cross_lang", "out_of_scope", "clarify"}
)


@dataclass(frozen=True, slots=True)
class Golden:
    id: str
    question: str
    language: Language
    bucket: Bucket
    expected_passage_ids: tuple[str, ...] = ()
    must_cite_at_least: int = 1
    expected_out_of_scope: bool = False
    expected_general_knowledge: bool = False
    expected_conflict_mention: bool = False
    notes: str = ""
    # Optional prior turns for multiturn tests. Each entry is
    # (role, content) where role is "user" or "assistant". Empty by
    # default — single-turn questions need no setup.
    prior_turns: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class GoldenSet:
    """In-memory collection with handy selection helpers used by the CLI."""

    items: tuple[Golden, ...]

    def __iter__(self) -> Iterator[Golden]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def by_id(self, gold_id: str) -> "GoldenSet":
        wanted = {x.strip() for x in gold_id.split(",") if x.strip()}
        return GoldenSet(tuple(g for g in self.items if g.id in wanted))

    def by_bucket(self, bucket: str) -> "GoldenSet":
        return GoldenSet(tuple(g for g in self.items if g.bucket == bucket))

    def balanced_sample(self, limit: int) -> "GoldenSet":
        """Round-robin a sample of size ``limit`` across buckets so smoke
        runs stay representative of the original distribution.

        Stable ordering: items are taken in their original YAML order
        within each bucket.
        """
        if limit >= len(self.items):
            return self
        by_bucket: dict[str, list[Golden]] = defaultdict(list)
        for g in self.items:
            by_bucket[g.bucket].append(g)
        out: list[Golden] = []
        # Round-robin until we hit ``limit``.
        while len(out) < limit:
            progressed = False
            for bucket in list(by_bucket.keys()):
                if not by_bucket[bucket]:
                    continue
                out.append(by_bucket[bucket].pop(0))
                progressed = True
                if len(out) >= limit:
                    break
            if not progressed:
                break
        return GoldenSet(tuple(out))


def load_golden_set(path: Path | str) -> GoldenSet:
    """Load + validate ``evals/golden_set.yaml``.

    Raises ``ValueError`` on malformed entries — we'd rather fail loudly
    at runner startup than emit garbage scores.
    """
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: top-level YAML must be a list of golden entries")

    items: list[Golden] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"{path} entry {index}: must be a mapping, got {type(entry).__name__}")
        gold_id = entry.get("id")
        if not isinstance(gold_id, str) or not gold_id:
            raise ValueError(f"{path} entry {index}: missing or non-string 'id'")
        if gold_id in seen_ids:
            raise ValueError(f"{path} entry {index}: duplicate id {gold_id!r}")
        seen_ids.add(gold_id)
        question = entry.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"{path} {gold_id}: missing or empty 'question'")
        language = entry.get("language")
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"{path} {gold_id}: invalid language {language!r}")
        bucket = entry.get("bucket")
        if bucket not in _VALID_BUCKETS:
            raise ValueError(f"{path} {gold_id}: invalid bucket {bucket!r}")
        expected_passage_ids = entry.get("expected_passage_ids") or ()
        if isinstance(expected_passage_ids, str):
            raise ValueError(f"{path} {gold_id}: 'expected_passage_ids' must be a list, got string")
        raw_prior = entry.get("prior_turns") or ()
        if isinstance(raw_prior, str) or not hasattr(raw_prior, "__iter__"):
            raise ValueError(
                f"{path} {gold_id}: 'prior_turns' must be a list of {{role, content}} dicts"
            )
        prior_turns: list[tuple[str, str]] = []
        for turn_idx, turn in enumerate(raw_prior):
            if not isinstance(turn, dict):
                raise ValueError(
                    f"{path} {gold_id}: prior_turns[{turn_idx}] must be a mapping with role/content"
                )
            role = turn.get("role")
            content = turn.get("content")
            if role not in ("user", "assistant"):
                raise ValueError(
                    f"{path} {gold_id}: prior_turns[{turn_idx}].role must be 'user' or 'assistant'"
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"{path} {gold_id}: prior_turns[{turn_idx}].content must be a non-empty string"
                )
            prior_turns.append((role, content.strip()))
        items.append(
            Golden(
                id=gold_id,
                question=question.strip(),
                language=language,  # type: ignore[arg-type]
                bucket=bucket,  # type: ignore[arg-type]
                expected_passage_ids=tuple(expected_passage_ids),
                must_cite_at_least=int(entry.get("must_cite_at_least", 1)),
                expected_out_of_scope=bool(entry.get("expected_out_of_scope", False)),
                expected_general_knowledge=bool(entry.get("expected_general_knowledge", False)),
                expected_conflict_mention=bool(entry.get("expected_conflict_mention", False)),
                notes=str(entry.get("notes", "")),
                prior_turns=tuple(prior_turns),
            )
        )
    return GoldenSet(tuple(items))


__all__ = ["Bucket", "Golden", "GoldenSet", "Language", "load_golden_set"]
