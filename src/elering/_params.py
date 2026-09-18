"""Query-parameter normalisation, timestamps and time-window splitting."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, TypeAlias

TimeLike: TypeAlias = "str | date | datetime"
Rows: TypeAlias = list[dict[str, Any]]
Groups: TypeAlias = dict[str, Rows]

NpsArea: TypeAlias = Literal["EE", "FI", "LV", "LT"]
CapacityArea: TypeAlias = Literal["FI", "LV", "RU"]
GasTradeArea: TypeAlias = Literal["COMMON", "EE", "FI", "LV", "LT"]
GreenType: TypeAlias = Literal["TRANSACTION", "PRODUCTION"]
UmmStatus: TypeAlias = Literal["current", "outdated"]
UmmEventStatus: TypeAlias = Literal["active", "inactive", "dismissed"]
UmmUnavailabilityType: TypeAlias = Literal["planned", "unplanned"]
UmmSort: TypeAlias = Literal[
    "publicationDateTimeDesc",
    "publicationDateTimeAsc",
    "eventStartDesc",
    "eventStartAsc",
    "eventStopDesc",
    "eventStopAsc",
]

NPS_AREAS: tuple[str, ...] = ("EE", "FI", "LV", "LT")
CAPACITY_AREAS: tuple[str, ...] = ("FI", "LV", "RU")
GAS_TRADE_AREAS: tuple[str, ...] = ("COMMON", "EE", "FI", "LV", "LT")
GREEN_TYPES: tuple[str, ...] = ("TRANSACTION", "PRODUCTION")
UMM_STATUSES: tuple[str, ...] = ("current", "outdated")
UMM_EVENT_STATUSES: tuple[str, ...] = ("active", "inactive", "dismissed")
UMM_UNAVAILABILITY_TYPES: tuple[str, ...] = ("planned", "unplanned")
UMM_EVENT_TYPES: tuple[str, ...] = (
    "Offshore_pipeline_unavailability",
    "Transmission_system_unavailability",
    "Storage_unavailability",
    "Injection_unavailability",
    "Withdrawal_unavailability",
    "Gas_treatment_plant_unavailability",
    "Regasification_plant_unavailability",
    "Compressor_station_unavailability",
    "Gas_production_field_unavailability",
    "Import_contract_curtailment",
    "Consumption_unavailability",
    "Other_unavailability",
)
UMM_SORTS: tuple[str, ...] = (
    "publicationDateTimeDesc",
    "publicationDateTimeAsc",
    "eventStartDesc",
    "eventStartAsc",
    "eventStopDesc",
    "eventStopAsc",
)

# The API parses start/end as a java.time.ZonedDateTime and rejects anything
# without an explicit offset.
_API_FORMAT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})$"
)


def to_datetime(value: TimeLike, *, name: str) -> datetime:
    """Coerce a user-supplied instant to an aware UTC :class:`~datetime.datetime`.

    Naive datetimes and plain dates are interpreted as UTC.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"{name}: expected an ISO 8601 date or datetime, got {value!r}"
            ) from exc
    else:
        raise TypeError(
            f"{name}: expected str, date or datetime, got {type(value).__name__}"
        )

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_datetime(value: TimeLike, *, name: str) -> str:
    """Render an instant in the exact format the API accepts."""
    if isinstance(value, str) and _API_FORMAT.match(value):
        return value
    return to_datetime(value, name=name).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_timestamp(value: float) -> datetime:
    """Convert an Elering ``timestamp`` (Unix seconds) to an aware UTC datetime."""
    return datetime.fromtimestamp(value, tz=timezone.utc)


def check_choice(
    value: str, allowed: Sequence[str], *, name: str, upper: bool = False
) -> str:
    """Validate an enumerated argument before a request is made."""
    candidate = value.upper() if upper else value
    if candidate not in allowed:
        raise ValueError(f"{name} must be one of {', '.join(allowed)}, got {value!r}")
    return candidate


def time_windows(
    start: datetime, end: datetime, max_window: timedelta | None
) -> Iterator[tuple[datetime, datetime]]:
    """Split ``[start, end]`` into consecutive windows of at most ``max_window``.

    The API treats ``end`` as inclusive, so consecutive windows repeat the row
    on their shared boundary; :func:`dedupe` removes it again.
    """
    if end <= start:
        raise ValueError("end must be later than start")
    if max_window is None or end - start <= max_window:
        yield start, end
        return
    cursor = start
    while cursor < end:
        stop = min(cursor + max_window, end)
        yield cursor, stop
        cursor = stop


def dedupe(rows: Rows) -> Rows:
    """Drop rows repeated on a window boundary, preserving order."""
    seen: set[Any] = set()
    unique: Rows = []
    for row in rows:
        stamp = row.get("timestamp")
        if stamp is not None:
            if stamp in seen:
                continue
            seen.add(stamp)
        unique.append(row)
    return unique


def query(**params: object) -> dict[str, object]:
    """Drop unset parameters so the API applies its own defaults."""
    return {key: value for key, value in params.items() if value is not None}
