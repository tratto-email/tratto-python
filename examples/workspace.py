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
workspace = tratto.workspace.get()
print(workspace["name"], "-", workspace["plan"])
for sender in workspace["senders"]:
    print(" ", sender["email"], sender["verified"])

# ── 2. Settings ───────────────────────────────────────────────────────────────
# The default sender must sit on a domain already verified for this workspace.
tratto.workspace.update(
    {
        "name": "Acme Inc.",
        "defaultFromName": "Acme",
        "defaultFromEmail": "hello@acme.com",
    }
)

tratto.workspace.update_preferences({"language": "it", "timezone": "Europe/Rome"})

# ── 3. Team ───────────────────────────────────────────────────────────────────
invite = tratto.workspace.invite_member("newcomer@acme.com", "member")
print("invited", invite["email"])

# Roles: owner, admin, member.
tratto.workspace.update_member("usr_123", "admin")


def remove_someone(user_id: str) -> None:
    """Not called here: the last owner cannot be removed, and a removed member
    loses access immediately.
    """
    tratto.workspace.remove_member(user_id)


def delete_everything() -> None:
    """Not called here, and not by accident either: this erases the workspace
    and every contact, template, campaign and email in it, permanently.
    """
    tratto.workspace.delete()
