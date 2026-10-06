# tratto-python

Official Python SDK for [Tratto](https://tratto.email) — the accessible transactional and marketing email platform for startups and non-profits.

[![PyPI](https://img.shields.io/pypi/v/tratto-email)](https://pypi.org/project/tratto-email/)
[![Python](https://img.shields.io/pypi/pyversions/tratto-email)](https://pypi.org/project/tratto-email/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

**No external dependencies** — uses Python's built-in `urllib`.
Requires **Python 3.10+**.

---

## Installation

```bash
pip install tratto-email
```

---

## Quick start

```python
import os
from tratto import Tratto, SendEmailOptions

client = Tratto(os.environ["TRATTO_API_KEY"])

result = client.emails.send(SendEmailOptions(
    from_="hello@yourdomain.com",
    to="user@example.com",
    subject="Welcome to our platform!",
    html="<h1>Welcome!</h1><p>Thanks for signing up.</p>",
))
print(result["id"])  # email_…
```

Every response is wrapped in an envelope: the payload is under `"data"`, and
on a list response `"data"` is the array with `"pagination"` beside it.

Or write the email in [emailmd](https://www.emailmd.dev/) markdown — rendered
server-side into responsive, email-safe HTML (plus a text part):

```python
client.emails.send(SendEmailOptions(
    from_="Acme <hello@mail.acme.com>",
    to="user@example.com",
    subject="Welcome!",
    markdown="# Welcome, {{first_name}}\n\nGlad to have you on board.",
))
```

``markdown`` is mutually exclusive with ``html``. Templates accept it too:
``CreateTemplateOptions(name=..., markdown=...)`` creates a ``format: 'emailmd'``
template whose HTML is rendered and pinned at save time.

---

## Authentication

Create an API key in the [Tratto dashboard](https://app.tratto.email/settings/api-keys) and pass it to the client.

```python
client = Tratto("tratto_live_…")
```

Never commit API keys to source control. Use environment variables:

```python
import os
client = Tratto(os.environ["TRATTO_API_KEY"])
```

---

## Test mode

Every workspace can create **test API keys** (`tratto_test_…`) alongside live ones. A test key runs the exact same pipeline — statuses, email timeline, webhooks — but **nothing is actually delivered**: no domain verification needed, no monthly quota consumed (test sends have their own daily cap).

```python
client = Tratto("tratto_test_…")

# Works immediately, even with an unverified sender domain
result = client.emails.send(SendEmailOptions(
    from_="Acme <hello@any-domain.dev>",
    to="delivered@simulator.tratto.email",
    subject="Hello from test mode",
    html="<p>It works!</p>",
))
# result["data"]["livemode"] is False
```

The recipient address picks the outcome (any other address simulates a normal delivery):

| Recipient | Outcome |
|---|---|
| `delivered@simulator.tratto.email` | `delivered` event |
| `bounced@simulator.tratto.email` | permanent bounce → email ends `failed` |
| `soft-bounced@simulator.tratto.email` | transient bounce |
| `complained@simulator.tratto.email` | spam complaint event |

Responses and webhook payloads carry `livemode: false`; a test key only ever sees test data; test emails are retained for 7 days; endpoints that reach real recipients (campaign send, template test-send, flow activation) reject test keys with `403 TEST_MODE_NOT_SUPPORTED`. Going live is a one-line change: swap in a `tratto_live_…` key (verified sender domain required).

---

## Emails

### Send a transactional email

```python
from tratto import SendEmailOptions

result = client.emails.send(SendEmailOptions(
    from_="Acme <hello@acme.com>",
    to=["alice@example.com", "bob@example.com"],
    subject="Your order has shipped",
    html="<p>Your order <strong>#1234</strong> is on its way!</p>",
    text="Your order #1234 is on its way!",
    reply_to="support@acme.com",
    tags=["order", "shipping"],
))
print(result["id"])  # email_…
```

**With a saved template:**

```python
result = client.emails.send(SendEmailOptions(
    from_="hello@acme.com",
    to="user@example.com",
    subject="Welcome to Acme!",
    template_id="tmpl_…",
    variables={"first_name": "Alice", "plan": "Pro"},
))
```

**Schedule for later:**

```python
result = client.emails.send(SendEmailOptions(
    from_="hello@acme.com",
    to="user@example.com",
    subject="Your weekly digest",
    html="<p>Here is this week's digest…</p>",
    scheduled_at="2025-01-20T09:00:00Z",
))
```

**Idempotent sends** (safe to retry without duplicates):

```python
import uuid

result = client.emails.send(SendEmailOptions(
    from_="hello@acme.com",
    to="user@example.com",
    subject="Password reset",
    html="<p>Click here to reset your password.</p>",
    idempotency_key=str(uuid.uuid4()),
))
```

### List emails

```python
response = client.emails.list(status="delivered", limit=20)

for email in response["data"]:
    print(email["id"], email["status"])

# Fetch next page
if response["pagination"]["hasMore"]:
    next_page = client.emails.list(
        after=response["pagination"]["nextCursor"]
    )
```

### Get an email and its events

```python
email = client.emails.get("email_…")
print(email["data"]["status"])  # delivered

events = client.emails.get_events("email_…")
for event in events["data"]:
    print(event["type"], event["occurredAt"])
```

---

## Contacts

### Create a contact

```python
from tratto import CreateContactOptions

result = client.contacts.create(CreateContactOptions(
    email="alice@example.com",
    first_name="Alice",
    last_name="Smith",
    status="subscribed",
    tags=["vip", "beta"],
    custom_fields={"plan": "pro", "company": "Acme"},
))
print(result["data"]["id"])  # cont_…
```

### List and filter contacts

```python
response = client.contacts.list(status="subscribed", tag="vip", limit=50)
for contact in response["data"]:
    print(contact["email"], contact["status"])
```

### Update a contact

```python
from tratto import UpdateContactOptions

client.contacts.update("cont_…", UpdateContactOptions(
    status="unsubscribed",
    tags=["churned"],
))
```

### Import contacts from CSV

```python
import time

csv_data = """email,firstName,lastName,tags
alice@example.com,Alice,Smith,vip;beta
bob@example.com,Bob,Jones,
"""

job = client.contacts.import_csv(csv_data)
job_id = job["data"]["jobId"]

# Poll until complete
while True:
    status = client.contacts.get_import_job(job_id)
    if status["data"]["status"] != "processing":
        break
    time.sleep(1)

print(f"Imported {status['data']['processedRows']} contacts")
if status["data"]["failedRows"]:
    print("Errors:", status["data"]["errors"])
```

---

## Audiences

```python
from tratto import CreateAudienceOptions, AudienceRule

# Create an audience with optional segmentation rules
audience = client.audiences.create(CreateAudienceOptions(
    name="Pro users",
    description="All users on the Pro plan",
    rules=[
        AudienceRule(field="plan", operator="equals", value="pro"),
    ],
))
audience_id = audience["data"]["id"]

# Add contacts
client.audiences.add_contacts(
    audience_id,
    contact_ids=["cont_…", "cont_…"],
)

# Get a single audience
audience = client.audiences.get(audience_id)
print(audience["data"]["contactCount"])
```

**Audience rule operators:** `equals`, `not_equals`, `contains`, `not_contains`, `array_contains`

---

## Templates

```python
from tratto import CreateTemplateOptions, UpdateTemplateOptions

# Create
template = client.templates.create(CreateTemplateOptions(
    name="Welcome email",
    html="<h1>Welcome, {{first_name}}!</h1>",
))
template_id = template["data"]["id"]

# Update (auto-increments version)
client.templates.update(template_id, UpdateTemplateOptions(
    html="<h1>Welcome, {{first_name}}!</h1><p>Glad you're here.</p>",
    status="published",
))

# Version history
versions = client.templates.list_versions(template_id)
v1 = client.templates.get_version(template_id, 1)

# Test send
client.templates.test_send(
    template_id,
    to="you@example.com",
    variables={"first_name": "Test"},
)

# Delete
client.templates.delete(template_id)
```

Responses are plain dicts with the API's camelCase keys. For `markdown` templates,
`create` and `update` also return the emailmd renderer's warnings when there are any:
`template["data"].get("renderWarnings", [])`.

---

## Domains

Before sending email you must register and verify your sender domain.

```python
# 1. Register the domain (generates DKIM keys)
domain = client.domains.add("acme.com")

# 2. Add the returned DNS records at your registrar
for record in domain["data"]["records"]:
    print(f"{record['type']} {record['host']} → {record['value']}")

# 3. Verify once DNS has propagated
result = client.domains.verify("dom_…")
print(result["data"]["status"])  # verified | failed

# List all domains
client.domains.list()

# Remove a domain
client.domains.delete("dom_…")
```

The verify step checks **SPF**, **DKIM**, and **DMARC** records. Each record
includes a `verified` boolean so you can see exactly which records are missing.

---

## Campaigns

```python
from tratto import CreateCampaignOptions

# Create (draft)
campaign = client.campaigns.create(CreateCampaignOptions(
    name="January newsletter",
    template_id="tmpl_…",
    audience_id="aud_…",
    from_name="Acme Newsletter",
    from_email="newsletter@acme.com",
    subject_a="Our top picks for January",
    subject_b="January: don't miss these",  # optional A/B subject
))
campaign_id = campaign["data"]["id"]

# Test before sending
client.campaigns.test_send(campaign_id, to="you@example.com")

# Send immediately
client.campaigns.send(campaign_id)

# Or schedule
client.campaigns.send(campaign_id, scheduled_at="2025-01-15T10:00:00Z")

# Cancel the schedule, back to draft (409 CONFLICT once the send started,
# or once a bounce-probe wave went out: pause it instead)
client.campaigns.unschedule(campaign_id)

# Pause
client.campaigns.pause(campaign_id)

# Stats
stats = client.campaigns.get_stats(campaign_id)
print(f"Open rate: {stats['data']['rates']['openRate']}%")
```

---

## Webhooks

```python
from tratto import CreateWebhookOptions

# Register
webhook = client.webhooks.create(CreateWebhookOptions(
    url="https://yourapp.com/webhooks/tratto",
    events=["delivered", "opened", "clicked", "bounced"],
))
webhook_id = webhook["data"]["id"]
secret = webhook["data"]["secret"]  # store this — returned only once

# Send a test event
client.webhooks.test(webhook_id)

# Delivery history
history = client.webhooks.list_deliveries(webhook_id)

# Rotate signing secret
new = client.webhooks.rotate_secret(webhook_id)
new_secret = new["data"]["secret"]

# Delete
client.webhooks.delete(webhook_id)
```

### Verifying webhook signatures

Tratto signs every request with HMAC-SHA256. Always verify the signature before
processing the payload:

```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Returns True if the signature is valid."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## Flows

Automations that react to contact and email events. A flow only runs once it is
*active*: `create` and `update` leave it in `draft`, and nothing is enrolled
until `activate` is called.

```python
flow = client.flows.create({
    "name": "Welcome sequence",
    "trigger": {"type": "contact_tag_added", "config": {"tagName": "signup"}},
    "steps": [
        {"type": "send_email", "config": {"templateId": "tmpl_abc"}},
        {"type": "wait", "config": {"delay": "2", "unit": "hours"}},
    ],
})

client.flows.activate(flow["data"]["id"])

# Pause it — contacts already mid-flow stay where they are
client.flows.deactivate(flow["data"]["id"])
```

---

## Analytics

```python
summary = client.analytics.get_summary("7d")     # 7d | 30d | 90d | 180d | 1y
series = client.analytics.get_timeseries("30d")  # same metrics, per day
```

`180d` and `1y` read the long-term aggregate, which holds live data only: with a
test-mode key they are rejected with `VALIDATION_ERROR` — use `90d` or shorter.

---

## Workspace

Settings and team membership.

```python
workspace = client.workspace.get()

# The default sender must be on a domain already verified for this workspace
client.workspace.update({"defaultFromEmail": "hello@yourdomain.com"})

# Roles: admin, member. The user id is read from the Team page of the dashboard
client.workspace.update_member("uid_1", "member")
```

Members are invited and removed from the dashboard by the workspace owner; the
API refuses these calls for API keys, so `invite_member()` and `remove_member()`
are deprecated.

API keys are deliberately **not** part of the SDK: they are issued from the
dashboard, where the raw value is shown once and its permissions are chosen
explicitly. For automated provisioning, call `/v1/api-keys` over HTTP directly.

---

## Error handling

All API errors raise `TrattoError`:

```python
from tratto import TrattoError

try:
    client.emails.get("email_doesnotexist")
except TrattoError as e:
    print(e)              # human-readable message
    print(e.code)         # machine-readable code, e.g. "NOT_FOUND"
    print(e.status_code)  # HTTP status, e.g. 404
    print(e.suggestion)   # what to do about it, or None if the API sends none
    print(e.docs)         # link to the error docs, or None
```

`suggestion` and `docs` are whatever the API sent, and are `None` when it sent
nothing — never an empty string. `suggestion` is the field to read where one
code covers several situations: both 409s on `campaigns.send` and
`campaigns.unschedule` are `CONFLICT`, and only the suggestion says whether to
wait and retry or to pause the campaign instead. Branch on `code` plus
`suggestion`, never on the message text.

**Common error codes:**

| Code | HTTP | Description |
|---|---|---|
| `UNAUTHORIZED` | 401 | Invalid or missing API key |
| `FORBIDDEN` | 403 | Key lacks the required permission, or domain not verified |
| `NOT_FOUND` | 404 | Resource does not exist |
| `CONFLICT` | 409 | Duplicate (e.g. contact email already exists) |
| `QUOTA_EXCEEDED` | 429 | A plan or test-mode limit was reached: the monthly email quota (on a send, or a campaign send with more recipients than remain this month), the plan's domain limit (`domains.create`), or, with a test key, the daily cap of 100 test sends (resets at midnight UTC) |
| `RATE_LIMITED` | 429 | Too many requests: more than 100 requests/second per API key, or more than 500 requests/minute per client IP (some endpoints set tighter limits) |
| `VALIDATION_ERROR` | 422 | Invalid request body |

Both `QUOTA_EXCEEDED` and `RATE_LIMITED` use HTTP 429, so check `e.code` rather than `e.status_code` to tell them apart: a `RATE_LIMITED` request succeeds if retried after a short back-off, while a `QUOTA_EXCEEDED` one keeps failing until the limit resets or the plan changes.

Full list: [error codes](https://docs.tratto.email/en/docs/error-codes).

---

## Pagination

All list endpoints return cursor-based pagination:

```python
response = client.contacts.list(limit=100)

while True:
    for contact in response["data"]:
        process(contact)

    if not response["pagination"]["hasMore"]:
        break

    response = client.contacts.list(
        limit=100,
        after=response["pagination"]["nextCursor"],
    )
```

---

## Framework integrations

### Django

Add the API key to your settings and initialise a shared client:

```python
# settings.py
TRATTO_API_KEY = env("TRATTO_API_KEY")  # e.g. via django-environ
```

```python
# emails.py
from django.conf import settings
from tratto import Tratto, SendEmailOptions, TrattoError

_client = Tratto(settings.TRATTO_API_KEY)


def send_welcome_email(user) -> str:
    """Send a welcome email and return the Tratto email ID."""
    result = _client.emails.send(SendEmailOptions(
        from_="Acme <hello@acme.com>",
        to=user.email,
        subject=f"Welcome, {user.first_name}!",
        template_id=settings.TRATTO_WELCOME_TEMPLATE_ID,
        variables={"first_name": user.first_name},
    ))
    return result["id"]
```

```python
# views.py
from django.contrib.auth import login
from django.http import JsonResponse
from .emails import send_welcome_email
from tratto import TrattoError

def register(request):
    # ... create user ...
    try:
        email_id = send_welcome_email(user)
    except TrattoError as e:
        # Log but don't block registration
        logger.error("Welcome email failed: %s", e)
    return JsonResponse({"id": user.pk})
```

For long-running background jobs (bulk sends, campaign triggers) use
[Celery](https://docs.celeryq.dev/) so the HTTP request doesn't block:

```python
# tasks.py
from celery import shared_task
from tratto import Tratto, SendEmailOptions
from django.conf import settings

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_order_confirmation(self, user_email: str, order_id: str):
    client = Tratto(settings.TRATTO_API_KEY)
    try:
        client.emails.send(SendEmailOptions(
            from_="orders@acme.com",
            to=user_email,
            subject=f"Order {order_id} confirmed",
            template_id=settings.TRATTO_ORDER_TEMPLATE_ID,
            variables={"order_id": order_id},
        ))
    except Exception as exc:
        raise self.retry(exc=exc)
```

---

### FastAPI

Use `lifespan` to create the client once at startup and inject it via
dependency injection:

```python
# main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from tratto import Tratto, SendEmailOptions, TrattoError


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tratto = Tratto(os.environ["TRATTO_API_KEY"])
    yield

app = FastAPI(lifespan=lifespan)


def get_tratto(request) -> Tratto:
    return request.app.state.tratto


@app.post("/users/{user_id}/welcome")
async def send_welcome(
    user_id: str,
    background_tasks: BackgroundTasks,
    client: Tratto = Depends(get_tratto),
):
    """Queue a welcome email in the background so the response is instant."""
    def _send():
        try:
            client.emails.send(SendEmailOptions(
                from_="hello@acme.com",
                to=f"{user_id}@example.com",
                subject="Welcome!",
                html="<p>Thanks for joining.</p>",
            ))
        except TrattoError as e:
            # Replace with your logger
            print(f"Email failed: {e}")

    background_tasks.add_task(_send)
    return {"status": "queued"}
```

For high-throughput endpoints run the blocking `urlopen` call in a thread pool
so it doesn't hold the event loop:

```python
import asyncio
from functools import partial

@app.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: str,
    client: Tratto = Depends(get_tratto),
):
    send = partial(
        client.emails.send,
        SendEmailOptions(
            from_="orders@acme.com",
            to="customer@example.com",
            subject=f"Order {order_id} confirmed",
            template_id="tmpl_order",
            variables={"order_id": order_id},
        ),
    )
    result = await asyncio.get_event_loop().run_in_executor(None, send)
    return {"email_id": result["id"]}
```

---

### Flask

Store the client on the application context using Flask's `g` or as a module-
level singleton:

```python
# extensions.py
import os
from tratto import Tratto

tratto = Tratto(os.environ["TRATTO_API_KEY"])
```

```python
# app.py
from flask import Flask, jsonify
from tratto import SendEmailOptions, TrattoError
from .extensions import tratto

app = Flask(__name__)


@app.post("/register")
def register():
    # ... create user ...
    try:
        result = tratto.emails.send(SendEmailOptions(
            from_="hello@acme.com",
            to=user["email"],
            subject="Welcome!",
            html=f"<p>Hi {user['name']}, thanks for signing up!</p>",
        ))
        app.logger.info("Welcome email sent: %s", result["id"])
    except TrattoError as e:
        app.logger.error("Email failed [%s]: %s", e.code, e)
    return jsonify({"id": user["id"]}), 201
```

For production workloads pair Flask with [Celery](https://docs.celeryq.dev/)
or [RQ](https://python-rq.org/) to send emails asynchronously:

```python
# tasks.py (RQ example)
from tratto import Tratto, SendEmailOptions
import os

def send_password_reset(email: str, reset_url: str):
    client = Tratto(os.environ["TRATTO_API_KEY"])
    client.emails.send(SendEmailOptions(
        from_="no-reply@acme.com",
        to=email,
        subject="Reset your password",
        html=f'<p><a href="{reset_url}">Reset password</a></p>',
    ))
```

```python
# view that enqueues the task
from flask import request, jsonify
from redis import Redis
from rq import Queue
from .tasks import send_password_reset

q = Queue(connection=Redis())

@app.post("/password-reset")
def request_password_reset():
    email = request.json["email"]
    reset_url = generate_reset_url(email)  # your logic
    q.enqueue(send_password_reset, email, reset_url)
    return jsonify({"status": "sent"}), 202
```

---

## API reference

### `Tratto(api_key, base_url?)`

| Attribute | Description |
|---|---|
| `client.emails` | Send and retrieve transactional emails |
| `client.contacts` | Create, update, and import contacts |
| `client.audiences` | Create and manage audience segments |
| `client.templates` | Manage reusable email templates |
| `client.domains` | Register and verify sender domains |
| `client.campaigns` | Create, send, and track marketing campaigns |
| `client.webhooks` | Register endpoints and inspect delivery history |
| `client.flows` | Build automations that react to contact and email events |
| `client.analytics` | Delivery and engagement metrics, as totals or a daily series |
| `client.workspace` | Workspace settings and team membership |

Full API documentation: [docs.tratto.email](https://docs.tratto.email)

---

## Examples

Runnable examples live in [`examples/`](./examples), one per resource:
[emails](./examples/emails.py), [contacts](./examples/contacts.py),
[audiences](./examples/audiences.py), [templates](./examples/templates.py),
[domains](./examples/domains.py), [campaigns](./examples/campaigns.py),
[webhooks](./examples/webhooks.py), [flows](./examples/flows.py),
[analytics](./examples/analytics.py), [workspace](./examples/workspace.py).

```bash
TRATTO_API_KEY=tratto_test_... python examples/emails.py
```

They are linted and typechecked with the package, so a renamed method or a
changed option type breaks the build instead of a customer's code.

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup instructions and guidelines.

---

## License

[MIT](./LICENSE)
