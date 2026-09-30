"""Read delivery and engagement metrics, as totals and as a daily series.

Run:
    TRATTO_API_KEY=tratto_test_... python examples/analytics.py
"""

import os

from tratto import Tratto

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Totals for a period ────────────────────────────────────────────────────
# 7d, 30d, 90d, 180d or 1y. A test key is limited to 90d and below.
# Every response is wrapped in an envelope: the payload is under "data".
summary = tratto.analytics.get_summary("30d")["data"]

print("Last 30 days")
print(f"  sent       {summary['totalSent']}")
print(f"  delivered  {summary['delivered']} ({summary['deliveryRate']:.1f}%)")
print(f"  opened     {summary['opened']} ({summary['openRate']:.1f}%)")
print(f"  clicked    {summary['clicked']} ({summary['clickRate']:.1f}%)")
print(f"  bounced    {summary['bounced']} ({summary['bounceRate']:.1f}%)")

# ── 2. The same numbers bucketed by day, to chart a trend ─────────────────────
series = tratto.analytics.get_timeseries("7d")
for day in series["data"]:
    print(day["date"], day["sent"], day["delivered"], day["opened"])
