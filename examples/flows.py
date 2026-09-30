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

# ── 1. Create — flows start in draft ──────────────────────────────────────────
# Trigger and steps are plain dicts, mirroring the API body.
flow = tratto.flows.create(
    {
        "name": "Welcome series",
        "trigger": {"type": "contact_created"},
        "steps": [
            {"type": "wait", "duration": "1h"},
            {"type": "send_email", "templateId": "tpl_welcome"},
            {"type": "wait", "duration": "3d"},
            {"type": "send_email", "templateId": "tpl_getting_started"},
        ],
    }
)
flow_id = flow["id"]
print("draft", flow_id)

# ── 2. Edit it ────────────────────────────────────────────────────────────────
tratto.flows.update(flow_id, {"name": "Welcome series (v2)"})
print("steps:", len(tratto.flows.get(flow_id)["steps"]))

# ── 3. List ───────────────────────────────────────────────────────────────────
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

    # Pausing leaves contacts already mid-flow exactly where they are.
    tratto.flows.deactivate(flow_id)

    # Deleting is permanent.
    tratto.flows.delete(flow_id)
