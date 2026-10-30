from api.reports.csv_report import _flatten_json_columns
from api.reports.formatters import to_bleaching_percents


def test_to_bleaching_percents_orders_keys_by_status_val():
    # jsonb-style key order (shortest key first)
    value = {
        "pale": 10.0,
        "normal": 50.0,
        "bleached": 50.0,
        "fully bleached": 20.0,
        "partially bleached": 15.0,
        "recent bleaching mortality": 5.0,
    }

    result = to_bleaching_percents(value, None, None, None)

    assert list(result) == [
        "bleached",
        "normal",
        "pale",
        "partially bleached",
        "fully bleached",
        "recent bleaching mortality",
    ]
    assert result["normal"] == 50.0


def test_to_bleaching_percents_none():
    assert to_bleaching_percents(None, None, None, None) is None


def test_bleaching_percents_csv_column_order():
    value = to_bleaching_percents({"pale": 1, "normal": 2, "bleached": 3}, None, None, None)
    headers = _flatten_json_columns(
        [["percent_bleached_hard_coral"], {"percent_bleached_hard_coral": value}]
    )[0]

    assert headers == [
        "percent_bleached_hard_coral_bleached",
        "percent_bleached_hard_coral_normal",
        "percent_bleached_hard_coral_pale",
        "percent_bleached_hard_coral_partially bleached",
        "percent_bleached_hard_coral_fully bleached",
        "percent_bleached_hard_coral_recent bleaching mortality",
    ]
