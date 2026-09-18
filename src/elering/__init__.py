"""Pythonic client for the Elering dashboard open API.

The API is public and read-only, so the module-level helpers are bound to a
shared default client and need no setup.
"""

from ._client import DEFAULT_BASE_URL, DEFAULT_MAX_WINDOW, Client, __version__
from ._errors import (
    EleringBadRequest,
    EleringError,
    EleringHTTPError,
    EleringServerError,
    EleringTransportError,
)
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
    from_timestamp,
)

_default = Client()

balance = _default.balance
capacity = _default.capacity
gas_balance = _default.gas_balance
gas_border_trade = _default.gas_border_trade
gas_system = _default.gas_system
gas_trade = _default.gas_trade
gas_transmission = _default.gas_transmission
green = _default.green
nominations = _default.nominations
nps = _default.nps
system = _default.system
transmission = _default.transmission
umm = _default.umm

__all__ = [
    "CAPACITY_AREAS",
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_WINDOW",
    "GAS_TRADE_AREAS",
    "GREEN_TYPES",
    "NPS_AREAS",
    "UMM_EVENT_STATUSES",
    "UMM_EVENT_TYPES",
    "UMM_SORTS",
    "UMM_STATUSES",
    "UMM_UNAVAILABILITY_TYPES",
    "Client",
    "EleringBadRequest",
    "EleringError",
    "EleringHTTPError",
    "EleringServerError",
    "EleringTransportError",
    "__version__",
    "balance",
    "capacity",
    "from_timestamp",
    "gas_balance",
    "gas_border_trade",
    "gas_system",
    "gas_trade",
    "gas_transmission",
    "green",
    "nominations",
    "nps",
    "system",
    "transmission",
    "umm",
]
