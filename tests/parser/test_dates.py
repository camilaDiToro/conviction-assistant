from datetime import date

import pytest

from app.parser.dates import extract_updated


@pytest.mark.parametrize(
    "text",
    [
        "*Updated: April 2026*",
        "*Atualizado: Abril 2026*",
        "**Atualização: Abril de 2026**",
        "*Last Updated: April 2026 | Decade Investment Research*",
    ],
)
def test_extract_updated_known_variants(text: str) -> None:
    assert extract_updated(text) == date(2026, 4, 1)


def test_extract_updated_returns_none_when_absent() -> None:
    assert extract_updated("plain text without a marker") is None


def test_extract_updated_takes_last_when_multiple() -> None:
    text = "Atualizado: Abril 2025\n\n## section\n\nÚltima Atualização: Abril de 2026"
    assert extract_updated(text) == date(2026, 4, 1)
