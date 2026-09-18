# exp.py
import elering
from elering import from_timestamp

# hit the real API
prices = elering.nps.price(start="2024-01-01", end="2024-01-02")
print(prices["ee"][:3])

latest = elering.system.latest()[0]
print(latest, "->", from_timestamp(latest["timestamp"]))

# exercise a custom client + windowing
from datetime import timedelta
with elering.Client(max_window=timedelta(days=200)) as c:
    rows = c.transmission.cross_border_hourly(start="2023-01-01", end="2024-01-01")
    print(len(rows), "rows")


