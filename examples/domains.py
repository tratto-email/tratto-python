"""Register a sender domain, publish its DNS records, verify it.

Run:
    TRATTO_API_KEY=tratto_live_... python examples/domains.py
"""

import os

from tratto import Tratto

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Register the domain — this generates the DKIM keys ─────────────────────
# Every response is wrapped in an envelope: the payload is under "data".
domain = tratto.domains.add("acme.com")["data"]
domain_id = domain["id"]

# ── 2. Publish these records at your DNS provider ─────────────────────────────
for record in domain["records"]:
    print(f"{record['purpose']:4} {record['type']:6} {record['host']}  ->  {record['value']}")

# ── 3. Ask Tratto to check them once DNS has propagated ───────────────────────
result = tratto.domains.verify(domain_id)
print("verification:", result["data"]["status"])

# Per-record detail, to see which one is still missing.
detail = tratto.domains.get(domain_id)["data"]
for record in detail["records"]:
    print(" ", record["purpose"], record["verified"])

# ── 4. List every sender domain in the workspace ──────────────────────────────
page = tratto.domains.list(limit=25)
print("domains:", [d["domain"] for d in page["data"]])
if page["pagination"]["hasMore"]:
    page = tratto.domains.list(limit=25, after=page["pagination"]["nextCursor"])


def remove_the_domain(domain_id: str) -> None:
    """Not called here: removing a domain revokes its DKIM private key, so
    mail already in flight from that domain stops authenticating.
    """
    tratto.domains.delete(domain_id)
