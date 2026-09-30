"""Create, update, list and bulk-import contacts.

The API has no delete route for contacts, so this example never removes one:
unsubscribing is how you stop mailing an address.

Run:
    TRATTO_API_KEY=tratto_test_... python examples/contacts.py
"""

import os
import time

from tratto import CreateContactOptions, Tratto, UpdateContactOptions

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Create ─────────────────────────────────────────────────────────────────
contact = tratto.contacts.create(
    CreateContactOptions(
        email="alice@example.com",
        first_name="Alice",
        last_name="Smith",
        tags=["vip", "beta"],
        custom_fields={"plan": "pro", "signup_source": "website"},
    )
)
contact_id = contact["id"]
print("created", contact_id)

# ── 2. Update — only the fields you pass change ───────────────────────────────
tratto.contacts.update(
    contact_id,
    UpdateContactOptions(last_name="Smith-Jones", custom_fields={"plan": "team"}),
)

# ── 3. List with filters, one page at a time ──────────────────────────────────
page = tratto.contacts.list(status="subscribed", tag="vip", limit=50)
seen = len(page["data"])
while page["pagination"]["hasMore"]:
    page = tratto.contacts.list(
        status="subscribed",
        tag="vip",
        limit=50,
        after=page["pagination"]["nextCursor"],
    )
    seen += len(page["data"])
print("subscribed vips:", seen)

# ── 4. Bulk import from CSV — asynchronous, poll the job ──────────────────────
job = tratto.contacts.import_csv(
    "email,firstName,lastName\nbob@example.com,Bob,Jones\ncarol@example.com,Carol,Doe\n"
)
while True:
    status = tratto.contacts.get_import_job(job["jobId"])
    if status["status"] in ("completed", "failed"):
        print("import", status["status"], status.get("imported"), "imported")
        break
    time.sleep(2)

# ── 5. Stop mailing someone ───────────────────────────────────────────────────
tratto.contacts.update(contact_id, UpdateContactOptions(status="unsubscribed"))
