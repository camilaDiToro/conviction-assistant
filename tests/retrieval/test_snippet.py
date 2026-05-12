"""Unit tests for app/retrieval/snippet.py::make_snippet."""

from app.retrieval.snippet import make_snippet


def test_make_snippet_returns_full_text_under_max():
    assert make_snippet("short text", max_chars=200) == "short text"


def test_make_snippet_truncates_at_word_boundary():
    text = "a" * 50 + " " + "b" * 50 + " " + "c" * 200
    snip = make_snippet(text, max_chars=120)
    assert snip.endswith("…")
    assert len(snip) <= 121
    assert " " in snip  # cut at a word boundary


def test_make_snippet_collapses_internal_whitespace():
    assert make_snippet("foo\n\n   bar", max_chars=200) == "foo bar"
