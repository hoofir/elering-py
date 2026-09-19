# elering-py
[![PyPI](https://img.shields.io/pypi/v/elering-py?label=PyPI)](https://pypi.org/project/elering-py/)
[![CI](https://github.com/hoofir/elering-py/actions/workflows/ci.yml/badge.svg)](https://github.com/hoofir/elering-py/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-purple)](https://github.com/astral-sh/ruff)
[![Ruff](https://img.shields.io/badge/format-ruff-purple)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/badge/type-ty-purple)](https://github.com/microsoft/ty)
[![Deptry](https://img.shields.io/badge/deps-deptry-tomato)](https://github.com/fpgmaas/deptry)
[![Pytest](https://img.shields.io/badge/tests-pytest-yellow)](https://github.com/pytest-dev/pytest)

A small Python client for the [Elering dashboard open API](https://dashboard.elering.ee/assets/swagger-ui/index.html) — Estonian electricity and gas system data published by Elering AS.

- **No dependencies.** Standard library only.
- **No setup.** The API is public and unauthenticated — `import elering` and go.
- **Readable calls.** Endpoint groups mirror the API docs, with snake case
  arguments and flexible dates.
- **Long ranges just work.** The API caps a request at one year; longer queries
  are split into windows and stitched back together for you.
- **Plain data out.** The `{"success": ..., "data": ...}` envelope is unwrapped
  and every call returns a `list[dict]`, ready for `pandas`, `polars` or `csv`.

---

## Quickstart

### Install

```bash
pip install elering-py
```

Requires Python 3.11 or newer.

### Query data

```python
import elering

# Nord Pool day-ahead prices for every Baltic area plus Finland
prices = elering.nps.price(start="2024-01-01", end="2024-01-02")

prices.keys()
# dict_keys(['ee', 'fi', 'lv', 'lt'])

prices["ee"][0]
# {'timestamp': 1704067200, 'price': 28.46}

# Estonian power system, right now
elering.system.latest()
# [{'timestamp': 1788104700, 'production': 375.25, 'consumption': 780.73,
#   'losses': None, 'frequency': 50.02, 'system_balance': -405.47,
#   'ac_balance': 232.37, 'production_renewable': 96.29,
#   'solar_energy_production': None}]
```

Into a dataframe:

```python
import pandas as pd

df = pd.DataFrame(prices["ee"])
df["time"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
```

---

## Guide

### Dates and times

`start` and `end` accept a string, a `date` or a `datetime`. Naive values are
treated as UTC; aware values are converted to UTC. **`end` is inclusive**, so
`start="2024-01-01", end="2024-01-02"` covers both days' boundary hours.

```python
from datetime import date, datetime

elering.system.values(start="2024-01-01", end=date(2024, 2, 1))
elering.system.values(start=datetime(2024, 1, 1, 6), end="2024-01-01T12:00")
```

Omitting both gives whatever the API considers current — usually the last day or
two. Passing only one of them raises `ValueError`.

```python
elering.nps.price()  # no range: the current window
```

### Timestamps

Every row is stamped with `timestamp`, a Unix time in seconds. Rows are returned
exactly as the API sends them; convert when you need to:

```python
from elering import from_timestamp

row = elering.system.latest()[0]
from_timestamp(row["timestamp"])
# datetime.datetime(2026, 4, 29, 5, 5, tzinfo=datetime.timezone.utc)
```

### Rows and groups

Most methods return a `list[dict]`. Endpoints that publish one series per area
return a `dict[str, list[dict]]` instead, keyed exactly as the API keys it:

| Method | Keys |
| --- | --- |
| `nps.price()`, `nps.turnover()` | `ee`, `fi`, `lv`, `lt` |
| `system.with_plan()` | `real`, `plan` |
| `transmission.capacity()` | `FI`, `LV`, `RU` |
| `gas_transmission.cross_border()` | `bc`, `karksi`, `misso`, `narva`, `varska` |
| `gas_trade.prices()` | `common`, `ee`, `fi`, `lv`, `lt` |

Where the API also offers a single-area variant, so does the client:

```python
elering.nps.price(start="2024-01-01", end="2024-01-02")["ee"]
elering.nps.price_latest("EE")

elering.transmission.capacity(start="2024-01-01", end="2024-01-02")["FI"]
elering.transmission.capacity_for("FI", start="2024-01-01", end="2024-01-02")
```

Area codes are case-insensitive and validated locally, so a typo raises
`ValueError` instead of costing a round trip.

### Long time ranges

The API rejects any request spanning more than a year with
`"Maximum period is 1 year"`. Ranges longer than `max_window` (default 365 days)
are therefore split into consecutive requests and concatenated in order. Because
`end` is inclusive, consecutive windows share one row; the duplicate is dropped
by `timestamp`, so the result is the same series you would get from a single
request:

```python
# transparently issued as several requests
rows = elering.transmission.cross_border_hourly(start="2015-01-01", end="2024-01-01")
```

### Urgent market messages

`umm.messages()` is the one paginated endpoint. It walks every page by default;
pass `page=` to fetch just one:

```python
elering.umm.messages(event_status="active", unavailability_type="planned")
elering.umm.messages(page=1)

# every message published for one event
elering.umm.event(2189)
```

### Errors

An empty result is returned as `[]` (or `{}`), not an error. Everything else
raises a subclass of `elering.EleringError`:

| Exception | Raised when |
| --- | --- |
| `EleringBadRequest` | HTTP 4xx — bad parameters. Exposes `.status` and `.messages` |
| `EleringServerError` | HTTP 5xx, after retries are exhausted |
| `EleringTransportError` | Network failure or timeout |

```python
try:
    elering.Client(max_window=None).nps.price(start="2020-01-01", end="2024-01-01")
except elering.EleringBadRequest as exc:
    print(exc.status)  # 400
    print(exc.messages)  # ['Maximum period is 1 year']
```

Invalid arguments (an unknown area, a lone `start`, an unparseable date) raise
`ValueError` before any request is made.

### Configuring a client

The module-level helpers use a shared default client. Create your own to change
its behaviour:

```python
from datetime import timedelta

with elering.Client(timeout=120, retries=5, max_window=timedelta(days=90)) as client:
    rows = client.gas_system.values(start="2024-01-01", end="2024-04-01")
```

| Argument | Default | Purpose |
| --- | --- | --- |
| `base_url` | `https://dashboard.elering.ee` | API root; must be http or https |
| `timeout` | `60.0` | Per-request socket timeout in seconds |
| `retries` | `3` | Extra attempts on transport errors and 5xx |
| `backoff` | `0.5` | Base delay for exponential retry backoff |
| `max_window` | `365 days` | Longest span per request; `None` disables splitting |

---

## Endpoints

| API group | Attribute | Methods |
| --- | --- | --- |
| Nord Pool | `nps` | `price()`, `price_latest()`, `price_current()`, `turnover()`, `turnover_latest()` |
| Power system | `system` | `values()`, `latest()`, `with_plan()` |
| Balance | `balance` | `balancing()`, `physical()`, `physical_latest()`, `commercial()`, `commercial_latest()` |
| Transmission | `transmission` | `cross_border()`, `cross_border_latest()`, `cross_border_hourly()`, `planned_trade()`, `planned_trade_latest()`, `capacity()`, `capacity_for()` |
| Gas system | `gas_system` | `values()`, `values_m3()`, `latest()`, `calorific_value()`, `calorific_value_25_0()` |
| Gas transmission | `gas_transmission` | `cross_border()`, `cross_border_latest()` |
| GET Baltic | `gas_trade` | `prices()`, `latest()` |
| Gas balance | `gas_balance` | `price()` |
| Gas border trade | `gas_border_trade` | `current()` |
| Gas capacity | `capacity` | `firm()`, `interruptible()` |
| Gas nominations | `nominations` | `values()`, `renominations()` |
| Green certificates | `green` | `certificates()` |
| Urgent market messages | `umm` | `messages()`, `event()`, `message()` |

Each attribute is available both on a `Client` instance and at module level
(`elering.nps.price(...)`).

### Not covered

- **CSV endpoints.** Every `/csv` path serves the same data as its JSON sibling,
  so the client exposes the JSON one and leaves formatting to you.
- **RSS feeds.** `/umm/gas/rss` is XML; the same messages are available as data
  through `umm.messages()`.

---

## Contributing

```bash
make setup     # create the venv and install dev dependencies
make check     # ruff lint, format check, ty type check, deptry
make test      # fast offline tests
make test-live # end-to-end tests against the real API
```

`make test` never touches the network. The live suite is deselected by default
and exercises every endpoint group, the windowing logic and the response shapes.

### Keeping up with the API

The endpoint methods are hand-written. The published spec declares every schema
as an empty object, so it documents paths and parameters but says nothing about
the data — the response shapes here were verified against the live API.

```bash
make spec-check   # fail if the published spec differs from spec/openapi.json
make spec         # refresh the vendored spec
```

CI runs `make spec-check` weekly, so spec changes show up as a reviewable diff.
Adding a new endpoint is then a few lines in `src/elering/_resources.py`.

### Known spec defects

Worked around in the hand-written layer, each verified against the live API:

- Responses are wrapped in `{"success": ..., "data": ...}`, which no schema
  mentions. The client unwraps it.
- `/api/balance/total` documents its first parameter as `fields`; it is `start`.
- `/api/umm/single/{id}` also requires `id` as a query parameter, and returns
  HTTP 500 without it.
- `/api/umm/gas/messages` documents its parameter as `id`; it is `event_id`.
- `start` and `end` are documented as accepting `yyyy-MM-dd HH:mm`; only
  offset-bearing ISO 8601 (`2024-01-01T00:00:00Z`) is actually parsed.
- The one-year limit and the inclusive `end` are undocumented.

---

## License

MIT — see [LICENSE](LICENSE). This project is not affiliated with Elering AS.
