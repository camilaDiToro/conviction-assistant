"""Tests for the pinned normalization policy in app/agent/verifier/normalize.py.

One test per rule in the policy + an idempotency property test. The
policy itself is documented in the module docstring; if a rule
changes, the docstring AND a test here must change together.
"""

from app.agent.verifier.normalize import normalize


def test_empty_string_returns_empty() -> None:
    assert normalize("") == ""


def test_nfc_combines_decomposed_diacritics() -> None:
    # "café" with a decomposed 'é' (U+0065 + U+0301) should round-trip
    # to the precomposed form (U+00E9).
    decomposed = "café"
    composed = "café"
    assert normalize(decomposed) == composed


def test_diacritics_are_preserved() -> None:
    # PT/ES users need diacritics to round-trip; stripping them would
    # let "nao" verify against "não", which we explicitly do not want.
    assert normalize("não é fácil") == "não é fácil"
    assert normalize("año tributário") == "año tributário"


def test_soft_hyphen_is_stripped() -> None:
    # U+00AD inside a word — common from PDF ingest.
    assert normalize("trib­ut­a­ção") == "tributação"


def test_zero_width_chars_are_stripped() -> None:
    # ZWSP, ZWNJ, ZWJ, BOM
    raw = "a​b‌c‍d﻿e"
    assert normalize(raw) == "abcde"


def test_smart_double_quotes_fold_to_ascii() -> None:
    assert normalize("“CDB”") == '"CDB"'
    assert normalize("«CDB»") == '"CDB"'


def test_smart_single_quotes_fold_to_ascii() -> None:
    assert normalize("‘CDB’") == "'CDB'"
    assert normalize("‹CDB›") == "'CDB'"


def test_em_and_en_dashes_become_hyphen_minus() -> None:
    assert normalize("CDB — tributação") == "CDB - tributação"
    assert normalize("CDB – tributação") == "CDB - tributação"


def test_nbsp_collapses_to_single_space() -> None:
    assert normalize("CDB tributação") == "CDB tributação"
    assert normalize("CDB tributação") == "CDB tributação"


def test_internal_whitespace_runs_collapse() -> None:
    assert normalize("CDB    tributação") == "CDB tributação"
    assert normalize("CDB\t\n  tributação") == "CDB tributação"


def test_leading_and_trailing_whitespace_stripped() -> None:
    assert normalize("  CDB tributação  ") == "CDB tributação"
    assert normalize("\n\tCDB\n") == "CDB"


def test_normalize_is_idempotent() -> None:
    """Running normalize twice gives the same result as running it once."""
    samples = [
        "  café “all”—día​  ",
        "trib­ut­a­ção  ",
        "plain ascii sentence.",
        "",
        "“mixed” – ‘case’ test",
    ]
    for s in samples:
        once = normalize(s)
        twice = normalize(once)
        assert once == twice, f"not idempotent: {s!r} -> {once!r} -> {twice!r}"


def test_ascii_punctuation_is_preserved() -> None:
    # ASCII quotes, hyphens, commas, periods etc. pass through unchanged.
    sample = "abc 123 .,-:;\"'!?()"
    assert normalize(sample) == sample
