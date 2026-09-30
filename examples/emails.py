"""Send a transactional email, then read back its status and its events.

Run:
    TRATTO_API_KEY=tratto_test_... python examples/emails.py
"""

import os

from tratto import SendEmailOptions, Tratto, TrattoError

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Send ───────────────────────────────────────────────────────────────────
# With a test key, address a simulator mailbox: nothing is delivered and the
# sender reputation is untouched.
try:
    sent = tratto.emails.send(
        SendEmailOptions(
            from_="Acme <hello@acme.com>",
            to="delivered@simulator.tratto.email",
            subject="Your order #1234 has shipped",
            html="<h1>On its way</h1><p>Track it any time.</p>",
            text="On its way. Track it any time.",
            reply_to="support@acme.com",
            tags=["order-shipped"],
            headers={"X-Order-Id": "1234"},
        )
    )
except TrattoError as err:
    # .code is machine-readable, .status_code is the HTTP status.
    raise SystemExit(f"send failed [{err.code}/{err.status_code}]: {err}") from err

# Every response is wrapped in an envelope: the payload is under "data".
email_id = sent["data"]["id"]
print("sent", email_id, "livemode:", sent["data"]["livemode"])

# ── 2. Send from a saved template, with variables ─────────────────────────────
tratto.emails.send(
    SendEmailOptions(
        from_="hello@acme.com",
        to=["delivered@simulator.tratto.email"],
        subject="Welcome aboard",
        template_id="tpl_123",
        variables={"first_name": "Alice", "plan": "pro"},
        # Retrying with the same key returns the first response, it does not
        # send a second email.
        idempotency_key="6f9619ff-8b86-d011-b42d-00c04fc964ff",
    )
)

# ── 3. Read the email back, plus its delivery timeline ────────────────────────
email = tratto.emails.get(email_id)
print("status:", email["data"]["status"])

# On a list response "data" is already the array, and "pagination" sits
# beside it.
for event in tratto.emails.get_events(email_id)["data"]:
    print(" ", event["type"], event["occurredAt"])

# ── 4. List ───────────────────────────────────────────────────────────────────
failed = tratto.emails.list(status="failed", limit=10, date_from="2026-01-01")
print("failed since January:", len(failed["data"]))
