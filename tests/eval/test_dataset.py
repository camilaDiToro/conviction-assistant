"""Tests for the golden-set loader and selection helpers."""

import textwrap
from pathlib import Path

import pytest

from evals.dataset import load_golden_set


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "golden_set.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_loader_parses_minimal_entry(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        - id: q01
          question: "What is a CDB?"
          language: en
          bucket: factual
        """,
    )
    gs = load_golden_set(p)
    assert len(gs) == 1
    g = next(iter(gs))
    assert g.id == "q01"
    assert g.language == "en"
    assert g.bucket == "factual"
    assert g.must_cite_at_least == 1
    assert g.expected_out_of_scope is False


def test_loader_rejects_duplicate_ids(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        - {id: q01, question: x, language: en, bucket: factual}
        - {id: q01, question: y, language: en, bucket: factual}
        """,
    )
    with pytest.raises(ValueError, match="duplicate id"):
        load_golden_set(p)


def test_loader_rejects_invalid_bucket(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        - {id: q01, question: x, language: en, bucket: nope}
        """,
    )
    with pytest.raises(ValueError, match="invalid bucket"):
        load_golden_set(p)


def test_by_bucket_filters(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        - {id: q01, question: x, language: en, bucket: factual}
        - {id: q02, question: y, language: en, bucket: rule_b}
        - {id: q03, question: z, language: en, bucket: rule_b}
        """,
    )
    gs = load_golden_set(p)
    rules = gs.by_bucket("rule_b")
    assert [g.id for g in rules] == ["q02", "q03"]


def test_balanced_sample_round_robins(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        - {id: f1, question: x, language: en, bucket: factual}
        - {id: f2, question: x, language: en, bucket: factual}
        - {id: f3, question: x, language: en, bucket: factual}
        - {id: r1, question: x, language: en, bucket: rule_a}
        - {id: r2, question: x, language: en, bucket: rule_a}
        - {id: b1, question: x, language: en, bucket: rule_b}
        """,
    )
    gs = load_golden_set(p)
    sample = gs.balanced_sample(3)
    # One per bucket (round-robin in insertion order).
    buckets = {g.bucket for g in sample}
    assert buckets == {"factual", "rule_a", "rule_b"}
    assert len(sample) == 3


def test_balanced_sample_limit_exceeds_len_returns_all(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        - {id: q01, question: x, language: en, bucket: factual}
        """,
    )
    gs = load_golden_set(p)
    sample = gs.balanced_sample(99)
    assert len(sample) == 1
