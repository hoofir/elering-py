"""Endpoint groups exposed on :class:`elering.Client`.

Each group mirrors one controller of the Elering dashboard API. Methods that
accept ``start`` and ``end`` return the series for that period; omitting both
returns whatever the API considers current.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._params import (
    CAPACITY_AREAS,
    GAS_TRADE_AREAS,
    GREEN_TYPES,
    NPS_AREAS,
    UMM_EVENT_STATUSES,
    UMM_EVENT_TYPES,
    UMM_SORTS,
    UMM_STATUSES,
    UMM_UNAVAILABILITY_TYPES,
    CapacityArea,
    GasTradeArea,
    GreenType,
    Groups,
    NpsArea,
    Rows,
    TimeLike,
    UmmEventStatus,
    UmmSort,
    UmmStatus,
    UmmUnavailabilityType,
    check_choice,
    format_datetime,
    query,
)

if TYPE_CHECKING:
    from ._client import Client


class _Group:
    def __init__(self, client: Client) -> None:
        self._client = client


class Nps(_Group):
    """Nord Pool day-ahead prices and volumes for the Baltics and Finland."""

    def price(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Groups:
        """Day-ahead price per bidding zone, keyed by ``ee``, ``fi``, ``lv``, ``lt``."""
        return self._client._groups_range("/api/nps/price", start=start, end=end)

    def price_latest(self, area: NpsArea) -> Rows:
        """Latest published day-ahead price for one bidding zone."""
        code = check_choice(area, NPS_AREAS, name="area", upper=True)
        return self._client._rows(f"/api/nps/price/{code}/latest")

    def price_current(self, area: NpsArea) -> Rows:
        """Day-ahead price of the current hour for one bidding zone."""
        code = check_choice(area, NPS_AREAS, name="area", upper=True)
        return self._client._rows(f"/api/nps/price/{code}/current")

    def turnover(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Groups:
        """Day-ahead buy (``in``) and sell (``out``) volumes per bidding zone."""
        return self._client._groups_range("/api/nps/turnover", start=start, end=end)

    def turnover_latest(self, area: NpsArea) -> Rows:
        code = check_choice(area, NPS_AREAS, name="area", upper=True)
        return self._client._rows(f"/api/nps/turnover/{code}/latest")


class System(_Group):
    """Estonian power system production, consumption and frequency."""

    def values(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        return self._client._rows_range("/api/system", start=start, end=end)

    def latest(self) -> Rows:
        return self._client._rows("/api/system/latest")

    def with_plan(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Groups:
        """Measured and planned system data, keyed by ``real`` and ``plan``."""
        return self._client._groups_range("/api/system/with-plan", start=start, end=end)


class Balance(_Group):
    """Balancing, physical and commercial balance of the power system."""

    def balancing(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Imbalance volumes, prices and regulation volumes."""
        return self._client._rows_range("/api/balance", start=start, end=end)

    def physical(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Monthly physical balance: inputs, outputs and renewable split."""
        return self._client._rows_range("/api/balance/total", start=start, end=end)

    def physical_latest(self) -> Rows:
        return self._client._rows("/api/balance/total/latest")

    def commercial(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Monthly commercial balance: imports and exports per country."""
        return self._client._rows_range("/api/balance/commerce", start=start, end=end)

    def commercial_latest(self) -> Rows:
        return self._client._rows("/api/balance/commerce/latest")


class Transmission(_Group):
    """Cross-border electricity flows, planned trade and capacities."""

    def cross_border(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Measured cross-border flows at 5-minute resolution."""
        return self._client._rows_range(
            "/api/transmission/cross-border", start=start, end=end
        )

    def cross_border_latest(self) -> Rows:
        return self._client._rows("/api/transmission/cross-border/latest")

    def cross_border_hourly(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Measured cross-border flows at hourly resolution."""
        return self._client._rows_range(
            "/api/transmission/cross-border/hourly", start=start, end=end
        )

    def planned_trade(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        return self._client._rows_range(
            "/api/transmission/cross-border-planned-trade", start=start, end=end
        )

    def planned_trade_latest(self) -> Rows:
        return self._client._rows("/api/transmission/cross-border-planned-trade/latest")

    def capacity(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Groups:
        """Transmission capacity for every border, keyed by ``FI``, ``LV``, ``RU``."""
        return self._client._groups_range(
            "/api/transmission/cross-border-capacity", start=start, end=end
        )

    def capacity_for(
        self,
        area: CapacityArea,
        *,
        start: TimeLike | None = None,
        end: TimeLike | None = None,
    ) -> Rows:
        """Transmission capacity for one border."""
        code = check_choice(area, CAPACITY_AREAS, name="area", upper=True)
        return self._client._rows_range(
            f"/api/transmission/cross-border-capacity/{code}", start=start, end=end
        )


class GasSystem(_Group):
    """Domestic gas flow out of the transmission network and its quality."""

    def values(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Hourly domestic gas flow in kWh."""
        return self._client._rows_range("/api/gas-system", start=start, end=end)

    def values_m3(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Hourly domestic gas flow in m3."""
        return self._client._rows_range("/api/gas-system/m3", start=start, end=end)

    def latest(self) -> Rows:
        return self._client._rows("/api/gas-system/latest")

    def calorific_value(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Daily weighted average gross calorific value (25/20)."""
        return self._client._rows_range("/api/gas-system/daily", start=start, end=end)

    def calorific_value_25_0(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        """Daily weighted average gross calorific value (25/0)."""
        return self._client._rows_range(
            "/api/gas-system/daily-average", start=start, end=end
        )


class GasTransmission(_Group):
    """Gas flow, pressure and quality at each cross-border entry point."""

    def cross_border(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Groups:
        """Keyed by entry point: ``bc``, ``karksi``, ``misso``, ``narva``, ``varska``."""
        return self._client._groups_range(
            "/api/gas-transmission/cross-border", start=start, end=end
        )

    def cross_border_latest(self) -> Groups:
        return self._client._groups("/api/gas-transmission/cross-border/latest")


class GasTrade(_Group):
    """GET Baltic gas exchange prices and traded quantities."""

    def prices(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Groups:
        """Keyed by ``common``, ``ee``, ``fi``, ``lv``, ``lt``."""
        return self._client._groups_range("/api/gas-trade", start=start, end=end)

    def latest(self, area: GasTradeArea) -> Rows:
        code = check_choice(area, GAS_TRADE_AREAS, name="area", upper=True)
        return self._client._rows(f"/api/gas-trade/{code}/latest")


class GasBalance(_Group):
    """Gas imbalance buy and sell prices."""

    def price(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        return self._client._rows_range("/api/gas-balance/price", start=start, end=end)


class GasBorderTrade(_Group):
    """Cross-border trade of the common Baltic-Finnish gas balancing zone."""

    def current(self) -> Rows:
        return self._client._rows("/api/gas/border-trade/current")


class Capacity(_Group):
    """Technical, booked and available gas transmission capacity."""

    def firm(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        return self._client._rows_range("/api/capacity/firm", start=start, end=end)

    def interruptible(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        return self._client._rows_range(
            "/api/capacity/interruptible", start=start, end=end
        )


class Nominations(_Group):
    """Gas nominations and renominations of the common balancing zone."""

    def values(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        return self._client._rows_range("/api/nominations", start=start, end=end)

    def renominations(
        self, *, start: TimeLike | None = None, end: TimeLike | None = None
    ) -> Rows:
        return self._client._rows_range(
            "/api/nominations/renominations", start=start, end=end
        )


class Green(_Group):
    """Green certificates issued for and transacted from renewable production."""

    def certificates(
        self,
        *,
        technology: str | None = None,
        fuel: str | None = None,
        type: GreenType = "TRANSACTION",  # noqa: A002 - matches the API parameter
    ) -> Rows:
        """Certificates of one ``type``, optionally filtered by technology or fuel.

        ``technology`` and ``fuel`` are Estonian-language labels; omitting them
        lets the API apply its "all" defaults.
        """
        return self._client._rows(
            "/api/green/certificates",
            query(
                technology=technology,
                fuel=fuel,
                type=check_choice(type, GREEN_TYPES, name="type", upper=True),
            ),
        )


class Umm(_Group):
    """Urgent market messages for the gas system."""

    def messages(
        self,
        *,
        status: UmmStatus = "current",
        event_status: UmmEventStatus | None = None,
        event_type: str | None = None,
        unavailability_type: UmmUnavailabilityType | None = None,
        affected_asset_name: str | None = None,
        event_start: TimeLike | None = None,
        event_end: TimeLike | None = None,
        published_after: TimeLike | None = None,
        sort: UmmSort = "publicationDateTimeDesc",
        page: int | None = None,
    ) -> Rows:
        """Messages matching the given filters.

        The endpoint is paginated. ``page=None`` (the default) walks every page
        and returns the messages as one list; pass a number to fetch just that
        page.
        """
        params = query(
            status=check_choice(status, UMM_STATUSES, name="status"),
            event_status=(
                None
                if event_status is None
                else check_choice(event_status, UMM_EVENT_STATUSES, name="event_status")
            ),
            event_type=(
                None
                if event_type is None
                else check_choice(event_type, UMM_EVENT_TYPES, name="event_type")
            ),
            unavailability_type=(
                None
                if unavailability_type is None
                else check_choice(
                    unavailability_type,
                    UMM_UNAVAILABILITY_TYPES,
                    name="unavailability_type",
                )
            ),
            affected_asset_name=affected_asset_name,
            event_duration_date_time_start=(
                None
                if event_start is None
                else format_datetime(event_start, name="event_start")
            ),
            event_duration_date_time_end=(
                None
                if event_end is None
                else format_datetime(event_end, name="event_end")
            ),
            publication_datetime_start=(
                None
                if published_after is None
                else format_datetime(published_after, name="published_after")
            ),
            sort=check_choice(sort, UMM_SORTS, name="sort"),
        )
        if page is not None:
            return self._client._rows("/api/umm/gas", {**params, "page": page})
        return self._all_pages(params)

    def event(self, event_id: int) -> Rows:
        """Every message published for one event.

        The path and the query string both carry the id; the API requires both.
        """
        return self._client._rows(f"/api/umm/single/{event_id}", query(id=event_id))

    def message(self, message_id: str) -> Rows:
        """One message, identified by its ``message_id``."""
        return self._client._rows("/api/umm/gas/messages", query(event_id=message_id))

    def _all_pages(self, params: dict[str, object]) -> Rows:
        rows: Rows = []
        page = 1
        while True:
            envelope = self._client._envelope("/api/umm/gas", {**params, "page": page})
            if not isinstance(envelope, dict):
                break
            rows.extend(envelope.get("data") or [])
            meta = envelope.get("meta")
            pages = meta.get("pages") if isinstance(meta, dict) else None
            if not isinstance(pages, int) or page >= pages:
                break
            page += 1
        return rows
