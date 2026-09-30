"""Create an audience, inspect it, and add contacts to it.

Run:
    TRATTO_API_KEY=tratto_test_... python examples/audiences.py
"""

import os

from tratto import AudienceRule, CreateAudienceOptions, Tratto

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Create, with segmentation rules ────────────────────────────────────────
# Contacts matching every rule are added automatically.
audience = tratto.audiences.create(
    CreateAudienceOptions(
        name="Pro customers in Italy",
        description="Everyone on the pro plan with an IT billing country",
        rules=[
            AudienceRule(field="plan", operator="equals", value="pro"),
            AudienceRule(field="country", operator="equals", value="IT"),
            AudienceRule(field="tags", operator="array_contains", value="vip"),
        ],
    )
)
# Every response is wrapped in an envelope: the payload is under "data".
audience_id = audience["data"]["id"]
print("created", audience_id)

# ── 2. A static audience: no rules, you add the members yourself ──────────────
static = tratto.audiences.create(CreateAudienceOptions(name="Launch invitees"))

# Up to 500 contact IDs per call.
added = tratto.audiences.add_contacts(static["data"]["id"], ["con_123", "con_456"])
print("added:", added["data"]["added"], "already there:", added["data"]["alreadyInAudience"])

# ── 3. Read back a single audience with its rules ─────────────────────────────
detail = tratto.audiences.get(audience_id)["data"]
for rule in detail["rules"]:
    print(" ", rule["field"], rule["operator"], rule["value"])

# ── 4. List ───────────────────────────────────────────────────────────────────
page = tratto.audiences.list(limit=25)
print("audiences on this page:", len(page["data"]))
if page["pagination"]["hasMore"]:
    page = tratto.audiences.list(limit=25, after=page["pagination"]["nextCursor"])
