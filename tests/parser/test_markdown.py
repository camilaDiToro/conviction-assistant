from datetime import date
from pathlib import Path

import pytest

from app.parser import parse_file
from app.parser.text import slugify


@pytest.mark.parametrize(
    "heading, expected",
    [
        ("O Que É um CDB", "o-que-e-um-cdb"),
        ("--Hello, World!--", "hello-world"),
        ("Ação Tributação", "acao-tributacao"),
    ],
)
def test_slugify(heading: str, expected: str) -> None:
    assert slugify(heading) == expected


def test_parse_file_basic_structure(tmp_path: Path) -> None:
    md = tmp_path / "sample.md"
    md.write_text(
        "# Sample Doc\n\n*Atualizado: Abril 2026*\n\n"
        "## First Section\n\nbody one\n\n"
        "## Second Section\n\nbody two\n\n### Subheading kept inline\n\nmore\n",
        encoding="utf-8",
    )
    passages = parse_file(md)

    assert [p.id for p in passages] == ["sample#first-section", "sample#second-section"]
    assert passages[0].document_title == "Sample Doc"
    assert passages[0].document_updated == date(2026, 4, 1)
    assert "Subheading kept inline" in passages[1].text


def test_duplicate_headings_get_suffix(tmp_path: Path) -> None:
    md = tmp_path / "dup.md"
    md.write_text("# Doc\n\n## Risks\n\nfirst\n\n## Risks\n\nsecond\n", encoding="utf-8")
    assert [p.id for p in parse_file(md)] == ["dup#risks", "dup#risks-2"]
