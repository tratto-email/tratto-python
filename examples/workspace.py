"""Read and change workspace settings, and manage the team.

Run:
    TRATTO_API_KEY=tratto_test_... python examples/workspace.py
"""

import os

from tratto import Tratto

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Who am I sending as ────────────────────────────────────────────────────
# Every response is wrapped in an envelope: the payload is under "data".
workspace = tratto.workspace.get()["data"]
print(workspace["name"], "-", workspace["plan"], "-", workspace["timezone"])

# The workspace-wide fallback…
print("default sender:", workspace["defaultFromName"], workspace["defaultFromEmail"])

# …and the per-send-type senders. A type set to None falls back to the default
# above, it is never a refusal.
for send_type in ("transactional", "marketing", "automation"):
    sender = workspace["senders"][send_type]
    print(f"  {send_type}:", sender["fromEmail"] if sender else "(default)")

# ── 2. Settings ───────────────────────────────────────────────────────────────
# The default sender must sit on a domain already verified for this workspace.
tratto.workspace.update(
    {
        "name": "Acme Inc.",
        "timezone": "Europe/Rome",
        "defaultFromName": "Acme",
        "defaultFromEmail": "hello@acme.com",
    }
)

# Preferences are the interface language and the notification emails we send
# you. The timezone lives on the workspace itself, above.
prefs = tratto.workspace.update_preferences(
    {"locale": "it", "emailNotifications": {"bounces": True, "weeklyReport": False}}
)
print("locale:", prefs["data"]["locale"])


def manage_the_team(user_id: str) -> None:
    """Not called here. Inviting is restricted: with an API key it always
    answers 403 MEMBER_INVITES_RESTRICTED, since an invite has to come from a
    signed-in user. ``workspace["canInviteMembers"]`` tells you whether this
    workspace may invite at all.
    """
    invite = tratto.workspace.invite_member("newcomer@acme.com", "member")
    print("invited", invite["data"]["email"], "as", invite["data"]["role"])

    # Roles: admin, member.
    tratto.workspace.update_member(user_id, "admin")

    # A removed member loses access immediately, and the last owner cannot go.
    tratto.workspace.remove_member(user_id)


# A workspace is deleted from the dashboard, by its owner. The API refuses
# DELETE /v1/workspace for every API key, so tratto.workspace.delete() is
# deprecated: it cannot succeed.
