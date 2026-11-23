"""
Regression tests for Trello card 2255.

User-entered free text (site/project/observer names, notes) was written into exported
CSV/XLSX unescaped, so a value starting with = + - @ (or tab/CR) ran as a formula when
the file was opened. A shared neutralize_formula helper now prefixes a single quote,
applied in the xlsx sink (cast_str_value) and the CSV sink (RawCSVReport).
"""

import pytest

from api.reports.rawcsv import RawCSVReport
from api.utils.castutils import cast_str_value, neutralize_formula


@pytest.mark.parametrize(
    "value",
    [
        '=HYPERLINK("http://evil/x")',
        "+1+1",
        "-cmd|'/c calc'!A0",
        "@SUM(A1)",
        "\tTAB",
        "\rCR",
    ],
)
def test_neutralize_prefixes_formula_characters(value):
    out = neutralize_formula(value)
    assert out == "'" + value


def test_neutralize_leaves_safe_values():
    assert neutralize_formula("Reef Site 1") == "Reef Site 1"
    assert neutralize_formula("") == ""
    assert neutralize_formula(5) == 5
    assert neutralize_formula(None) is None


def test_cast_str_value_neutralizes_text_but_keeps_numbers():
    assert cast_str_value("=cmd") == "'=cmd"
    assert cast_str_value("123") == 123  # numeric string -> number, no quote
    assert cast_str_value("-5") == -5  # legitimate negative number
    assert cast_str_value("Site A") == "Site A"


def test_rawcsv_flatten_neutralizes_string_cells():
    report = RawCSVReport()
    row = report._flatten_record({"name": '=HYPERLINK("http://evil")', "n": 5})
    assert row["name"].startswith("'=")
    assert row["n"] == 5
