"""Register a webhook endpoint, test it, inspect deliveries, rotate its secret.

Run:
    TRATTO_API_KEY=tratto_test_... python examples/webhooks.py
"""

import hashlib
import hmac
import os

from tratto import CreateWebhookOptions, Tratto

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Register ───────────────────────────────────────────────────────────────
webhook = tratto.webhooks.create(
    CreateWebhookOptions(
        url="https://acme.com/hooks/tratto",
        events=["delivered", "bounced", "complained", "opened", "clicked"],
    )
)
# Every response is wrapped in an envelope: the payload is under "data".
webhook_id = webhook["data"]["id"]

# The signing secret is returned once, at creation. Store it now.
secret = webhook["data"]["secret"]
print("registered", webhook_id)

# ── 2. Send a synthetic event to check the endpoint answers ───────────────────
tratto.webhooks.test(webhook_id)

# ── 3. Delivery history, most recent first ────────────────────────────────────
deliveries = tratto.webhooks.list_deliveries(webhook_id, limit=20)
for delivery in deliveries["data"]:
    print(" ", delivery["eventType"], delivery["status"], delivery["httpStatus"])
if deliveries["pagination"]["hasMore"]:
    deliveries = tratto.webhooks.list_deliveries(
        webhook_id, limit=20, after=deliveries["pagination"]["nextCursor"]
    )

# ── 4. List, rotate, delete ───────────────────────────────────────────────────
print("webhooks:", [w["url"] for w in tratto.webhooks.list()["data"]])

# Rotating invalidates the old secret immediately: deploy the new one first.
secret = tratto.webhooks.rotate_secret(webhook_id)["data"]["secret"]

tratto.webhooks.delete(webhook_id)


# ── 5. On your side: verify the signature before trusting the payload ─────────
def is_signature_valid(raw_body: bytes, header: str, secret: str) -> bool:
    """Compare the ``X-Tratto-Signature`` header against the raw request body."""
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
