"""End-to-end tests against the real Elering API.

Deselected by default; run them with ``make test-live``. They assert on the
shape of the responses rather than on values, which change constantly.
"""

from datetime import timedelta

import pytest

import elering
from elering import from_timestamp

pytestmark = pytest.mark.live

START = "2024-01-01"
END = "2024-01-02"


@pytest.fixture(scope="module")
def client():
    with elering.Client(timeout=120) as instance:
        yield instance


def assert_rows(rows, *, expected_keys=frozenset()):
    assert isinstance(rows, list)
    assert rows, "expected at least one row"
    for row in rows:
        assert isinstance(row, dict)
    assert expected_keys <= rows[0].keys()


def assert_groups(groups, *, expected_areas=frozenset()):
    assert isinstance(groups, dict)
    assert expected_areas <= groups.keys()
    for rows in groups.values():
        assert isinstance(rows, list)


# -- electricity ------------------------------------------------------------


def test_nps_price(client):
    groups = client.nps.price(start=START, end=END)
    assert_groups(groups, expected_areas={"ee", "fi", "lv", "lt"})
    assert_rows(groups["ee"], expected_keys={"timestamp", "price"})


@pytest.mark.parametrize("area", elering.NPS_AREAS)
def test_nps_price_latest(client, area):
    assert_rows(client.nps.price_latest(area), expected_keys={"timestamp", "price"})


def test_nps_price_current(client):
    assert_rows(client.nps.price_current("EE"), expected_keys={"timestamp", "price"})


def test_nps_turnover(client):
    groups = client.nps.turnover(start=START, end=END)
    assert_groups(groups, expected_areas={"ee", "fi", "lv", "lt"})
    assert_rows(groups["ee"], expected_keys={"timestamp", "in", "out"})


def test_nps_turnover_latest(client):
    assert_rows(client.nps.turnover_latest("EE"), expected_keys={"timestamp", "in"})


def test_system(client):
    rows = client.system.values(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "production", "consumption"})


def test_system_latest(client):
    assert_rows(client.system.latest(), expected_keys={"timestamp", "frequency"})


def test_system_with_plan(client):
    groups = client.system.with_plan(start=START, end=END)
    assert_groups(groups, expected_areas={"real", "plan"})
    assert_rows(groups["plan"], expected_keys={"timestamp", "production"})


def test_balance_balancing(client):
    assert_rows(
        client.balance.balancing(start=START, end=END), expected_keys={"timestamp"}
    )


def test_balance_physical(client):
    rows = client.balance.physical(start=START, end="2024-03-01")
    assert_rows(rows, expected_keys={"timestamp", "input_total", "output_total"})


def test_balance_physical_latest(client):
    assert_rows(client.balance.physical_latest(), expected_keys={"timestamp"})


def test_balance_commercial_latest(client):
    assert_rows(client.balance.commercial_latest(), expected_keys={"timestamp"})


def test_transmission_cross_border(client):
    rows = client.transmission.cross_border(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "finland", "latvia"})


def test_transmission_cross_border_hourly(client):
    rows = client.transmission.cross_border_hourly(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "finland"})


def test_transmission_cross_border_latest(client):
    assert_rows(client.transmission.cross_border_latest(), expected_keys={"timestamp"})


def test_transmission_planned_trade(client):
    rows = client.transmission.planned_trade(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "ee_fi", "ee_lv"})


def test_transmission_planned_trade_latest(client):
    assert_rows(client.transmission.planned_trade_latest(), expected_keys={"timestamp"})


def test_transmission_capacity(client):
    groups = client.transmission.capacity(start=START, end=END)
    assert_groups(groups, expected_areas=set(elering.CAPACITY_AREAS))
    assert_rows(groups["FI"], expected_keys={"timestamp", "in_atc", "out_ntc"})


@pytest.mark.parametrize("area", elering.CAPACITY_AREAS)
def test_transmission_capacity_for(client, area):
    rows = client.transmission.capacity_for(area, start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "in_atc"})


# -- gas --------------------------------------------------------------------


def test_gas_system(client):
    rows = client.gas_system.values(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "value"})


def test_gas_system_latest(client):
    assert_rows(client.gas_system.latest(), expected_keys={"timestamp"})


def test_gas_system_calorific_value(client):
    rows = client.gas_system.calorific_value(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "calorific_value"})


def test_gas_system_calorific_value_25_0(client):
    rows = client.gas_system.calorific_value_25_0(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "calorific_value_25_0"})


def test_gas_transmission_cross_border(client):
    groups = client.gas_transmission.cross_border(start=START, end=END)
    assert_groups(groups, expected_areas={"bc", "karksi", "narva"})
    assert_rows(groups["bc"], expected_keys={"timestamp", "volume", "direction"})


def test_gas_transmission_cross_border_latest(client):
    assert_groups(client.gas_transmission.cross_border_latest())


def test_gas_trade_prices(client):
    groups = client.gas_trade.prices(start=START, end=END)
    assert_groups(groups, expected_areas={"common", "ee", "fi", "lv", "lt"})
    assert_rows(groups["common"], expected_keys={"timestamp", "price"})


def test_gas_trade_latest(client):
    assert_rows(client.gas_trade.latest("EE"), expected_keys={"timestamp", "price"})


def test_gas_balance_price(client):
    rows = client.gas_balance.price(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "imbalance_buy_price"})


def test_gas_border_trade_current(client):
    assert_rows(client.gas_border_trade.current(), expected_keys={"timestamp"})


def test_capacity_firm(client):
    rows = client.capacity.firm(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "narva_technical_entry"})


def test_capacity_interruptible(client):
    rows = client.capacity.interruptible(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "narva_technical_entry"})


def test_nominations(client):
    rows = client.nominations.values(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "narva_entry", "consumption"})


def test_renominations(client):
    rows = client.nominations.renominations(start=START, end=END)
    assert_rows(rows, expected_keys={"timestamp", "narva_entry"})


def test_green_certificates(client):
    assert isinstance(client.green.certificates(), list)


def test_umm_messages(client):
    rows = client.umm.messages(page=1)
    assert_rows(rows, expected_keys={"id", "message_id", "event_status"})


def test_umm_event(client):
    event_id = client.umm.messages(page=1)[0]["id"]
    assert_rows(client.umm.event(event_id), expected_keys={"id", "message_id"})


# -- behaviour --------------------------------------------------------------


def test_long_range_is_split_and_stitched(client):
    with elering.Client(max_window=timedelta(days=200)) as windowed:
        rows = windowed.nps.price(start="2023-01-01", end="2024-01-01")["ee"]

    stamps = [row["timestamp"] for row in rows]
    assert stamps == sorted(stamps)
    assert len(stamps) == len(set(stamps)), "boundary rows must not be duplicated"


def test_timestamps_convert_to_datetimes(client):
    row = client.system.latest()[0]
    assert from_timestamp(row["timestamp"]).year >= 2020


def test_over_long_range_is_rejected_by_the_api(client):
    with elering.Client(max_window=None) as unwindowed:
        with pytest.raises(elering.EleringBadRequest) as excinfo:
            unwindowed.nps.price(start="2020-01-01", end="2024-01-01")

    assert excinfo.value.status == 400
    assert "Maximum period is 1 year" in str(excinfo.value)
