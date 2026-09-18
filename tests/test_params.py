from datetime import date, datetime, timedelta, timezone

import pytest

from elering._params import (
    check_choice,
    dedupe,
    format_datetime,
    from_timestamp,
    query,
    time_windows,
    to_datetime,
)

UTC = timezone.utc


# -- datetimes --------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2024-01-01", "2024-01-01T00:00:00Z"),
        ("2024-03-09T06:30", "2024-03-09T06:30:00Z"),
        (date(2024, 3, 9), "2024-03-09T00:00:00Z"),
        (datetime(2024, 3, 9, 6, 30), "2024-03-09T06:30:00Z"),
        (datetime(2024, 3, 9, 6, 30, tzinfo=UTC), "2024-03-09T06:30:00Z"),
    ],
)
def test_format_datetime(value, expected):
    assert format_datetime(value, name="start") == expected


def test_format_datetime_converts_aware_values_to_utc():
    aware = datetime(2024, 1, 1, 2, 0, tzinfo=timezone(timedelta(hours=2)))
    assert format_datetime(aware, name="start") == "2024-01-01T00:00:00Z"


@pytest.mark.parametrize(
    "value",
    ["2024-01-01T00:00:00Z", "2024-01-01T00:00:00.000Z", "2024-01-01T00:00:00+02:00"],
)
def test_format_datetime_passes_through_api_format(value):
    assert format_datetime(value, name="start") == value


def test_format_datetime_rejects_unparseable_strings():
    with pytest.raises(ValueError, match="expected an ISO 8601"):
        format_datetime("last tuesday", name="start")


def test_to_datetime_rejects_other_types():
    with pytest.raises(TypeError, match="expected str, date or datetime"):
        to_datetime(1704067200, name="start")  # ty: ignore[invalid-argument-type]


def test_from_timestamp():
    assert from_timestamp(1704067200) == datetime(2024, 1, 1, tzinfo=UTC)


# -- enumerated arguments ---------------------------------------------------


def test_check_choice_accepts_a_known_value():
    assert check_choice("current", ("current", "outdated"), name="status") == "current"


def test_check_choice_normalises_case_when_asked():
    assert check_choice("ee", ("EE", "FI"), name="area", upper=True) == "EE"


def test_check_choice_rejects_unknown_values():
    with pytest.raises(ValueError, match="area must be one of EE, FI"):
        check_choice("XX", ("EE", "FI"), name="area", upper=True)


# -- windows ----------------------------------------------------------------


def test_short_range_is_a_single_window():
    start, end = datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
    assert list(time_windows(start, end, timedelta(days=365))) == [(start, end)]


def test_max_window_none_disables_splitting():
    start, end = datetime(2010, 1, 1, tzinfo=UTC), datetime(2024, 1, 1, tzinfo=UTC)
    assert list(time_windows(start, end, None)) == [(start, end)]


def test_windows_are_contiguous_and_cover_the_range():
    start, end = datetime(2020, 1, 1, tzinfo=UTC), datetime(2024, 1, 1, tzinfo=UTC)
    windows = list(time_windows(start, end, timedelta(days=365)))

    assert len(windows) == 5
    assert windows[0][0] == start
    assert windows[-1][1] == end
    for previous, current in zip(windows[:-1], windows[1:]):
        assert previous[1] == current[0]


def test_end_must_be_later_than_start():
    moment = datetime(2024, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="end must be later than start"):
        list(time_windows(moment, moment, None))


# -- rows -------------------------------------------------------------------


def test_dedupe_drops_the_repeated_boundary_row():
    rows = [{"timestamp": 1}, {"timestamp": 2}, {"timestamp": 2}, {"timestamp": 3}]
    assert dedupe(rows) == [{"timestamp": 1}, {"timestamp": 2}, {"timestamp": 3}]


def test_dedupe_keeps_rows_without_a_timestamp():
    rows = [{"a": 1}, {"a": 1}]
    assert dedupe(rows) == rows


def test_query_drops_unset_parameters():
    assert query(a=1, b=None, c="x") == {"a": 1, "c": "x"}
