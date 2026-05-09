from pathlib import Path

import pytest

from app.services.parser import parse_corpus, parse_file, supported_extensions


def test_md_is_registered() -> None:
    assert "md" in supported_extensions()


def test_unknown_extension_raises(tmp_path: Path) -> None:
    unknown = tmp_path / "doc.xyz"
    unknown.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="no parser"):
        parse_file(unknown)


def test_parse_corpus_skips_unknown_extensions(tmp_path: Path) -> None:
    (tmp_path / "good.md").write_text("# d\n\n## s\n\nbody\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("plain", encoding="utf-8")
    out = parse_corpus(tmp_path)
    assert len(out) == 1
    assert out[0].document_id == "good"
