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
```

**Common error codes:**

| Code | HTTP | Description |
|---|---|---|
| `UNAUTHORIZED` | 401 | Invalid or missing API key |
| `FORBIDDEN` | 403 | Key lacks the required permission, or domain not verified |
| `NOT_FOUND` | 404 | Resource does not exist |
| `CONFLICT` | 409 | Duplicate (e.g. contact email already exists) |
| `QUOTA_EXCEEDED` | 429 | Monthly email quota reached |
| `VALIDATION_ERROR` | 422 | Invalid request body |

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

Full API documentation: [tratto.email/docs](https://tratto.email/docs)

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup instructions and guidelines.

---

## License

[MIT](./LICENSE)
