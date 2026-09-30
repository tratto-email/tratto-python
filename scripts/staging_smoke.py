#!/usr/bin/env python3
"""One real round-trip against the staging API, run by hand before a release.

Everything else in this repo mocks the network, so nothing notices when the
API renames a field. This does: it creates a contact and a template, sends an
email, reads the result back, and removes what it can.

It is deliberately not wired into CI. Run it yourself:

    cp .env.example .env     # fill it in, it is gitignored
    python scripts/staging_smoke.py

The key must be a test key (``tratto_test_…``): sends then go to the simulator
mailboxes and no real inbox, quota or sender reputation is touched.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from tratto import (
    CreateContactOptions,
    CreateTemplateOptions,
    SendEmailOptions,
    Tratto,
    TrattoError,
    UpdateContactOptions,
    UpdateTemplateOptions,
)

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
SIMULATOR = "delivered@simulator.tratto.email"


def load_env(path: Path) -> None:
    """Read ``KEY=value`` lines into the environment. Real variables win."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep:
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def required(name: str) -> str:
    """Return the variable, or stop naming the one that is missing."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing {name}. Copy .env.example to .env and fill it in, "
            f"or export {name} before running."
        )
    return value


def step(label: str) -> None:
    print(f"  {label}", flush=True)


def main() -> int:
    load_env(ENV_FILE)

    api_key = required("TRATTO_API_KEY")
    from_email = required("TRATTO_FROM_EMAIL")
    base_url = os.environ.get("TRATTO_BASE_URL", "https://api-staging.tratto.email")

    if not api_key.startswith("tratto_test_"):
        raise SystemExit(
            "TRATTO_API_KEY must be a test key (tratto_test_…). A live key would "
            "send for real and move the account's bounce rate."
        )

    tratto = Tratto(api_key, base_url)
    run_id = uuid.uuid4().hex[:8]
    print(f"Smoke run {run_id} against {base_url}")

    # Undo actions, newest first. Registered as soon as something exists, so a
    # failure halfway through still gets cleaned up.
    undo: list[tuple[str, Callable[[], object]]] = []
    failure: str | None = None

    try:
        workspace = tratto.workspace.get()
        step(f"workspace: {workspace['name']} (plan {workspace['plan']})")

        # ── Contact ───────────────────────────────────────────────────────────
        contact = tratto.contacts.create(
            CreateContactOptions(
                email=f"sdk-smoke-{run_id}@simulator.tratto.email",
                first_name="SDK",
                last_name="Smoke",
                tags=["sdk-smoke"],
                custom_fields={"run_id": run_id},
            )
        )
        contact_id = contact["id"]
        # The API has no delete for contacts: unsubscribing is the most we can
        # undo. The address is a simulator one, so the residue is inert.
        undo.append(
            (
                f"unsubscribe contact {contact_id}",
                lambda: tratto.contacts.update(
                    contact_id, UpdateContactOptions(status="unsubscribed")
                ),
            )
        )
        step(f"contact created: {contact_id}")

        # ── Template ──────────────────────────────────────────────────────────
        template = tratto.templates.create(
            CreateTemplateOptions(
                name=f"SDK smoke {run_id}",
                html="<h1>Hi {{first_name}}</h1><p>Smoke run " + run_id + "</p>",
            )
        )
        template_id = template["id"]
        undo.append(
            (
                f"delete template {template_id}",
                lambda: tratto.templates.delete(template_id),
            )
        )

        tratto.templates.update(template_id, UpdateTemplateOptions(status="published"))
        step(f"template created and published: {template_id}")

        # ── Send ──────────────────────────────────────────────────────────────
        sent = tratto.emails.send(
            SendEmailOptions(
                from_=from_email,
                to=SIMULATOR,
                subject=f"SDK smoke {run_id}",
                template_id=template_id,
                variables={"first_name": "SDK"},
                tags=["sdk-smoke"],
            )
        )
        email_id = sent["id"]
        if sent.get("livemode") is not False:
            raise RuntimeError(
                f"expected livemode false on a test key, got {sent.get('livemode')!r}"
            )
        step(f"email sent: {email_id} (livemode false)")

        # ── Read the state back ───────────────────────────────────────────────
        status = ""
        for _ in range(10):
            email = tratto.emails.get(email_id)
            status = email["status"]
            if status != "queued":
                break
            time.sleep(2)
        step(f"email status: {status}")

        events = tratto.emails.get_events(email_id)["data"]
        step(f"events: {[e['type'] for e in events] or 'none yet'}")

        listed = tratto.emails.list(tags="sdk-smoke", limit=5)["data"]
        if not any(e["id"] == email_id for e in listed):
            raise RuntimeError(f"email {email_id} is missing from the tagged list")
        step("email found in the tagged list")

    except (TrattoError, RuntimeError, KeyError) as err:
        failure = f"{type(err).__name__}: {err}"

    finally:
        print("Cleanup")
        for label, action in reversed(undo):
            try:
                action()
                step(f"ok: {label}")
            except TrattoError as err:
                step(f"FAILED: {label} -> [{err.code}] {err}")
                failure = failure or f"cleanup failed: {label}"

    if failure:
        print(f"\nFAILED: {failure}")
        return 1

    print(f"\nOK. Residue: one unsubscribed contact sdk-smoke-{run_id}@simulator.tratto.email")
    return 0


if __name__ == "__main__":
    sys.exit(main())
