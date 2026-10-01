"""Create a marketing campaign, send or schedule it, and read its stats.

Run:
    TRATTO_API_KEY=tratto_test_... python examples/campaigns.py
"""

import os

from tratto import CreateCampaignOptions, Tratto, TrattoError

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Create — campaigns start as drafts ─────────────────────────────────────
# The template must be published and the sender domain verified.
campaign = tratto.campaigns.create(
    CreateCampaignOptions(
        name="February newsletter",
        template_id="tpl_123",
        audience_id="aud_123",
        from_name="Acme Newsletter",
        from_email="news@acme.com",
        subject_a="What shipped in February",
        subject_b="February at Acme",  # A/B test, optional
    )
)
# Every response is wrapped in an envelope: the payload is under "data".
campaign_id = campaign["data"]["id"]
print("draft", campaign_id)

# ── 2. Read it back, and list the drafts you have queued ──────────────────────
print("status:", tratto.campaigns.get(campaign_id)["data"]["status"])

drafts = tratto.campaigns.list(status="draft", limit=25)
print("drafts:", len(drafts["data"]))
if drafts["pagination"]["hasMore"]:
    drafts = tratto.campaigns.list(
        status="draft", limit=25, after=drafts["pagination"]["nextCursor"]
    )

# ── 3. Stats, once it has gone out ────────────────────────────────────────────
stats = tratto.campaigns.get_stats(campaign_id)["data"]
print("delivered:", stats["stats"]["delivered"], "opened:", stats["stats"]["opened"])
print("open rate:", stats["rates"]["openRate"], "%")


def send_it(campaign_id: str) -> None:
    """Not called here: a campaign reaches real recipients, so it needs a live
    key. A test key is rejected with 403 TEST_MODE_NOT_SUPPORTED.
    """
    # A preview to one address before committing to the whole audience.
    tratto.campaigns.test_send(campaign_id, "you@acme.com")

    # Send now…
    tratto.campaigns.send(campaign_id)

    # …or schedule it.
    tratto.campaigns.send(campaign_id, scheduled_at="2026-03-01T09:00:00Z")

    # Cancel a schedule and go back to draft. Once the send has started, or a
    # bounce-probe wave has gone out, this returns 409 CONFLICT: pause instead.
    # Those cases share the CONFLICT code, so read `err.suggestion` — the API
    # spells out what to do there — instead of matching on the message text.
    try:
        tratto.campaigns.unschedule(campaign_id)
    except TrattoError as err:
        print(f"unschedule refused [{err.code}]: {err}")
        if err.suggestion:
            print("what to do:", err.suggestion)
        if err.docs:
            print("more:", err.docs)

    # Stop a campaign that is already sending.
    tratto.campaigns.pause(campaign_id)
