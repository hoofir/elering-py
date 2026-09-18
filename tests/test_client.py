from datetime import timedelta

import pytest

import elering
from elering import _client
from elering._client import _as_groups, _as_rows, _unwrap

BASE = "https://dashboard.elering.ee"


@pytest.fixture
def recorder(monkeypatch):
    """Replace the transport and record every URL the client requests."""
    calls: list[str] = []
    responses: list[object] = []

    def fake_get_json(url, **_kwargs):
        calls.append(url)
        return responses.pop(0) if responses else {"success": True, "data": []}

    monkeypatch.setattr(_client, "get_json", fake_get_json)
    return calls, responses


# -- URL building -----------------------------------------------------------


def test_latest_endpoint_builds_url(recorder):
    calls, _ = recorder
    elering.Client().system.latest()
    assert calls == [f"{BASE}/api/system/latest"]


def test_time_range_is_formatted_for_the_api(recorder):
    calls, _ = recorder
    elering.Client().system.values(start="2024-01-01", end="2024-01-02")
    assert calls == [
        f"{BASE}/api/system?start=2024-01-01T00%3A00%3A00Z&end=2024-01-02T00%3A00%3A00Z"
    ]


def test_omitting_the_range_omits_the_parameters(recorder):
    calls, _ = recorder
    elering.Client().nps.price()
    assert calls == [f"{BASE}/api/nps/price"]


def test_start_and_end_must_be_given_together(recorder):
    calls, _ = recorder
    with pytest.raises(ValueError, match="start and end must be given together"):
        elering.Client().system.values(start="2024-01-01")
    assert calls == []


def test_area_is_upper_cased_into_the_path(recorder):
    calls, _ = recorder
    elering.Client().nps.price_latest("ee")  # ty: ignore[invalid-argument-type]
    assert calls == [f"{BASE}/api/nps/price/EE/latest"]


def test_unknown_area_is_rejected_before_any_request(recorder):
    calls, _ = recorder
    with pytest.raises(ValueError, match="area must be one of"):
        elering.Client().nps.price_latest("XX")  # ty: ignore[invalid-argument-type]
    assert calls == []


def test_unset_filters_are_omitted(recorder):
    calls, _ = recorder
    elering.Client().green.certificates()
    assert calls == [f"{BASE}/api/green/certificates?type=TRANSACTION"]


def test_base_url_scheme_is_validated():
    with pytest.raises(ValueError, match="http or https"):
        elering.Client(base_url="file:///etc").system.latest()


# -- windowing --------------------------------------------------------------


def test_long_range_is_split_into_windows(recorder):
    calls, _ = recorder
    client = elering.Client(max_window=timedelta(days=30))
    client.system.values(start="2024-01-01", end="2024-03-01")

    assert len(calls) == 2
    assert "start=2024-01-01T00%3A00%3A00Z" in calls[0]
    assert "end=2024-01-31T00%3A00%3A00Z" in calls[0]
    assert "start=2024-01-31T00%3A00%3A00Z" in calls[1]
    assert "end=2024-03-01T00%3A00%3A00Z" in calls[1]


def test_windowed_rows_are_concatenated_without_the_boundary_duplicate(recorder):
    _, responses = recorder
    responses.extend(
        [
            {"data": [{"timestamp": 1}, {"timestamp": 2}]},
            {"data": [{"timestamp": 2}, {"timestamp": 3}]},
        ]
    )
    client = elering.Client(max_window=timedelta(days=30))
    rows = client.system.values(start="2024-01-01", end="2024-03-01")
    assert rows == [{"timestamp": 1}, {"timestamp": 2}, {"timestamp": 3}]


def test_windowed_groups_are_merged_per_area(recorder):
    _, responses = recorder
    responses.extend(
        [
            {"data": {"ee": [{"timestamp": 1}], "fi": [{"timestamp": 1}]}},
            {"data": {"ee": [{"timestamp": 1}, {"timestamp": 2}]}},
        ]
    )
    client = elering.Client(max_window=timedelta(days=30))
    groups = client.nps.price(start="2024-01-01", end="2024-03-01")
    assert groups == {
        "ee": [{"timestamp": 1}, {"timestamp": 2}],
        "fi": [{"timestamp": 1}],
    }


def test_max_window_none_issues_a_single_request(recorder):
    calls, _ = recorder
    elering.Client(max_window=None).system.values(start="2010-01-01", end="2024-01-01")
    assert len(calls) == 1


# -- payload normalisation --------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"success": True, "data": [{"a": 1}]}, [{"a": 1}]),
        ({"success": True, "data": None}, None),
        ([{"a": 1}], [{"a": 1}]),
        (None, None),
    ],
)
def test_unwrap(payload, expected):
    assert _unwrap(payload) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (None, []),
        ([], []),
        ([{"a": 1}], [{"a": 1}]),
        ({"a": 1}, [{"a": 1}]),
    ],
)
def test_as_rows(data, expected):
    assert _as_rows(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (None, {}),
        ([], {}),
        ({"ee": [{"a": 1}]}, {"ee": [{"a": 1}]}),
        # /api/gas-transmission/cross-border/latest returns one object per key
        ({"bc": {"a": 1}, "narva": None}, {"bc": [{"a": 1}], "narva": []}),
    ],
)
def test_as_groups(data, expected):
    assert _as_groups(data) == expected


# -- urgent market messages -------------------------------------------------


def test_umm_walks_every_page(recorder):
    calls, responses = recorder
    responses.extend(
        [
            {"data": [{"id": 1}], "meta": {"page": 1, "pages": 2}},
            {"data": [{"id": 2}], "meta": {"page": 2, "pages": 2}},
        ]
    )
    rows = elering.Client().umm.messages()

    assert rows == [{"id": 1}, {"id": 2}]
    assert "page=1" in calls[0]
    assert "page=2" in calls[1]


def test_umm_can_fetch_a_single_page(recorder):
    calls, _ = recorder
    elering.Client().umm.messages(page=3)
    assert len(calls) == 1
    assert "page=3" in calls[0]


def test_umm_event_repeats_the_id_in_the_query(recorder):
    calls, _ = recorder
    elering.Client().umm.event(2189)
    assert calls == [f"{BASE}/api/umm/single/2189?id=2189"]
