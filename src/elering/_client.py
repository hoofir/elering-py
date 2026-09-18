"""The synchronous Elering dashboard API client."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version
from types import TracebackType
from typing import Any, Self

from . import _resources as res
from ._http import build_url, get_json
from ._params import (
    Groups,
    Rows,
    TimeLike,
    dedupe,
    format_datetime,
    time_windows,
    to_datetime,
)

DEFAULT_BASE_URL = "https://dashboard.elering.ee"
DEFAULT_MAX_WINDOW = timedelta(days=365)

try:
    __version__ = version("elering-py")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"


class Client:
    """Access the Elering dashboard open API.

    The API is public, read-only and unauthenticated. Responses are unwrapped
    from their ``{"success": ..., "data": ...}`` envelope and returned either as
    a list of rows or, for endpoints that split their data by area, as a mapping
    of area to rows. Timestamps stay as the API's Unix seconds; use
    :func:`elering.from_timestamp` to convert them.

    Args:
        base_url: API root; must be http or https.
        timeout: Per-request socket timeout in seconds.
        retries: Extra attempts on transport errors and 5xx responses.
        backoff: Base delay in seconds for exponential retry backoff.
        max_window: Longest span per request. The API rejects anything over a
            year, so longer ranges are split and stitched back together.
            ``None`` always issues a single request.
        user_agent: Value of the ``User-Agent`` header.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        retries: int = 3,
        backoff: float = 0.5,
        max_window: timedelta | None = DEFAULT_MAX_WINDOW,
        user_agent: str = f"elering-py/{__version__}",
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.max_window = max_window
        self.user_agent = user_agent

        self.balance = res.Balance(self)
        self.capacity = res.Capacity(self)
        self.gas_balance = res.GasBalance(self)
        self.gas_border_trade = res.GasBorderTrade(self)
        self.gas_system = res.GasSystem(self)
        self.gas_trade = res.GasTrade(self)
        self.gas_transmission = res.GasTransmission(self)
        self.green = res.Green(self)
        self.nominations = res.Nominations(self)
        self.nps = res.Nps(self)
        self.system = res.System(self)
        self.transmission = res.Transmission(self)
        self.umm = res.Umm(self)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    # -- internals ----------------------------------------------------------

    def _envelope(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = build_url(self.base_url, path, params)
        return get_json(
            url,
            timeout=self.timeout,
            retries=self.retries,
            backoff=self.backoff,
            user_agent=self.user_agent,
        )

    def _data(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return _unwrap(self._envelope(path, params))

    def _rows(self, path: str, params: dict[str, Any] | None = None) -> Rows:
        return _as_rows(self._data(path, params))

    def _groups(self, path: str, params: dict[str, Any] | None = None) -> Groups:
        return _as_groups(self._data(path, params))

    def _rows_range(
        self,
        path: str,
        *,
        start: TimeLike | None,
        end: TimeLike | None,
        params: dict[str, Any] | None = None,
    ) -> Rows:
        rows: Rows = []
        for window in self._windows(start, end):
            rows.extend(self._rows(path, {**(params or {}), **window}))
        return dedupe(rows)

    def _groups_range(
        self,
        path: str,
        *,
        start: TimeLike | None,
        end: TimeLike | None,
        params: dict[str, Any] | None = None,
    ) -> Groups:
        merged: Groups = {}
        for window in self._windows(start, end):
            for area, rows in self._groups(path, {**(params or {}), **window}).items():
                merged.setdefault(area, []).extend(rows)
        return {area: dedupe(rows) for area, rows in merged.items()}

    def _windows(
        self, start: TimeLike | None, end: TimeLike | None
    ) -> Iterator[dict[str, str]]:
        """Yield the ``start``/``end`` parameters of each request to make."""
        if start is None and end is None:
            yield {}
            return
        if start is None or end is None:
            raise ValueError("start and end must be given together")
        for first, last in time_windows(
            to_datetime(start, name="start"),
            to_datetime(end, name="end"),
            self.max_window,
        ):
            yield {
                "start": format_datetime(first, name="start"),
                "end": format_datetime(last, name="end"),
            }


def _unwrap(payload: Any) -> Any:
    """Strip the ``{"success": ..., "data": ...}`` envelope."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _as_rows(data: Any) -> Rows:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def _as_groups(data: Any) -> Groups:
    if not isinstance(data, dict):
        return {}
    return {area: _as_rows(value) for area, value in data.items()}
