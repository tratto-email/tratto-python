"""Build an automation that reacts to a contact or email event.

Flows are the one v1 resource with no fine-grained scopes: every call here
needs an API key carrying the ``*`` permission. Create one for the job and
revoke it right after.

Run:
    TRATTO_API_KEY=tratto_live_... python examples/flows.py
"""

import os

from tratto import Tratto

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Create — a flow is born named, in draft, with no trigger and no steps ──
# Every response is wrapped in an envelope: the payload is under "data".
flow = tratto.flows.create({"name": "Welcome series"})
flow_id = flow["data"]["id"]
print("draft", flow_id)

# ── 2. Give it a trigger and its steps ────────────────────────────────────────
# Trigger types: contact_joins_audience, contact_tag_added, contact_tag_removed,
# email_event, manual. Step types: send_email, wait, branch, update_contact,
# webhook_call. Both carry their parameters in `config`, whose values are
# strings. Steps cannot be edited while the flow is active: deactivate first.
updated = tratto.flows.update(
    flow_id,
    {
        "trigger": {"type": "contact_joins_audience", "config": {"audienceId": "aud_123"}},
        "steps": [
            {"id": "wait-an-hour", "type": "wait", "config": {"duration": "1h"}},
            {"id": "welcome", "type": "send_email", "config": {"templateId": "tpl_welcome"}},
            {"id": "wait-3-days", "type": "wait", "config": {"duration": "3d"}},
            {"id": "tips", "type": "send_email", "config": {"templateId": "tpl_tips"}},
        ],
    },
)
print("steps:", len(updated["data"]["steps"]))

# ── 3. Read it back ───────────────────────────────────────────────────────────
detail = tratto.flows.get(flow_id)["data"]
print(detail["name"], detail["status"], "enrollments:", detail["enrollments"])

# ── 4. List — status is draft, active or inactive ─────────────────────────────
page = tratto.flows.list(status="active", limit=25)
print("active flows:", len(page["data"]))
if page["pagination"]["hasMore"]:
    page = tratto.flows.list(
        status="active", limit=25, after=page["pagination"]["nextCursor"]
    )


def go_live_and_back(flow_id: str) -> None:
    """Not called here: activating a flow enrols real contacts and sends to
    them, so a test key is rejected with 403 TEST_MODE_NOT_SUPPORTED.
    """
    # From now on the trigger starts enrolling contacts.
    tratto.flows.activate(flow_id)

    # Pausing leaves contacts already mid-flow exactly where they are, and is
    # what you need before editing the steps again.
    tratto.flows.deactivate(flow_id)

    # Deleting is permanent.
    tratto.flows.delete(flow_id)
