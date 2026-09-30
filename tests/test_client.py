import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from tratto import (
    AudienceRule,
    CreateAudienceOptions,
    CreateCampaignOptions,
    CreateContactOptions,
    CreateTemplateOptions,
    CreateWebhookOptions,
    SendEmailOptions,
    Tratto,
    TrattoError,
    UpdateContactOptions,
    UpdateTemplateOptions,
)

# ── Helpers ───────────────────────────────────────────────────────────────────────────────

PATCH_URLOPEN = "tratto._http.urlopen"


def _mock_response(data: dict, status: int = 200):
    m = MagicMock()
    m.read.return_value = json.dumps(data).encode()
    m.status = status
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    return m


def _http_error(body: dict, code: int) -> HTTPError:
    return HTTPError(
        url="", code=code, msg="", hdrs=None, fp=BytesIO(json.dumps(body).encode())
    )


# ── Client init ────────────────────────────────────────────────────────────────────────────

class TestClientInit:
    def test_requires_api_key(self):
        with pytest.raises(ValueError):
            Tratto("")

    def test_creates_resource_attributes(self):
        client = Tratto("tratto_live_test")
        assert client.emails is not None
        assert client.contacts is not None
        assert client.audiences is not None
        assert client.templates is not None
        assert client.domains is not None
        assert client.campaigns is not None
        assert client.webhooks is not None
        assert client.flows is not None
        assert client.analytics is not None
        assert client.workspace is not None

    def test_does_not_expose_api_keys(self):
        # API keys are issued from the dashboard, never from application code —
        # the resource is deliberately absent from both SDKs.
        client = Tratto("tratto_live_test")
        assert not hasattr(client, "api_keys")
        assert not hasattr(client, "apiKeys")

    def test_user_agent_carries_package_version(self):
        # The version has a single source (pyproject.toml, read via
        # importlib.metadata): __version__ and the User-Agent must both follow it.
        from importlib.metadata import version

        import tratto

        assert tratto.__version__ == version("tratto-email")
        with patch(PATCH_URLOPEN, return_value=_mock_response({"data": {}})) as mock_open:
            Tratto("tratto_live_test").workspace.get()
        req = mock_open.call_args[0][0]
        assert req.get_header("User-agent") == f"tratto-python/{version('tratto-email')}"


# ── Emails ────────────────────────────────────────────────────────────────────────────────

class TestEmails:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_send_email_returns_id(self):
        resp = {"data": {"id": "email_abc123"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.emails.send(SendEmailOptions(
                from_="sender@example.com",
                to="user@example.com",
                subject="Hello",
                html="<p>Hello</p>",
            ))
        assert result["id"] == "email_abc123"

    def test_send_with_template(self):
        resp = {"data": {"id": "email_abc123"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.emails.send(SendEmailOptions(
                from_="sender@example.com",
                to="user@example.com",
                subject="Hello",
                template_id="tmpl_xyz",
                variables={"name": "Alice"},
            ))
        assert result["id"] == "email_abc123"

    def test_send_sets_idempotency_header(self):
        resp = {"data": {"id": "email_abc123"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as mock_open:
            self.client.emails.send(SendEmailOptions(
                from_="sender@example.com",
                to="user@example.com",
                subject="Hello",
                html="<p>Hello</p>",
                idempotency_key="idem-key-123",
            ))
        req = mock_open.call_args[0][0]
        assert req.get_header("Idempotency-key") == "idem-key-123"

    def test_send_markdown_goes_in_body_without_html(self):
        resp = {"data": {"id": "email_md1"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as mock_open:
            self.client.emails.send(SendEmailOptions(
                from_="sender@example.com",
                to="success@simulator.amazonses.com",
                subject="md",
                markdown="# Hi {{name}}",
            ))
        req = mock_open.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["markdown"] == "# Hi {{name}}"
        assert "html" not in body

    def test_list_emails(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.emails.list(status="delivered", limit=10)
        assert "data" in result
        assert "pagination" in result

    def test_get_email(self):
        resp = {"data": {"id": "email_abc123", "status": "delivered", "events": []}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.emails.get("email_abc123")
        assert result["data"]["id"] == "email_abc123"

    def test_get_events(self):
        resp = {"data": [{"type": "delivered", "occurredAt": "2025-01-01T00:00:00Z"}]}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.emails.get_events("email_abc123")
        assert result["data"][0]["type"] == "delivered"

    def test_api_error_raises_tratto_error(self):
        error = _http_error({"error": {"code": "NOT_FOUND", "message": "Email not found"}}, 404)
        with patch(PATCH_URLOPEN, side_effect=error), pytest.raises(TrattoError) as exc_info:
            self.client.emails.get("email_notexist")
        assert exc_info.value.code == "NOT_FOUND"
        assert exc_info.value.status_code == 404
        assert "Email not found" in str(exc_info.value)

    def test_unauthorized_raises_tratto_error(self):
        error = _http_error({"error": {"code": "UNAUTHORIZED", "message": "Invalid API key"}}, 401)
        with patch(PATCH_URLOPEN, side_effect=error), pytest.raises(TrattoError) as exc_info:
            self.client.emails.list()
        assert exc_info.value.status_code == 401


# ── Contacts ─────────────────────────────────────────────────────────────────────────────

class TestContacts:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_contact(self):
        resp = {"data": {"id": "cont_abc123"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 201)):
            result = self.client.contacts.create(CreateContactOptions(
                email="alice@example.com",
                first_name="Alice",
                last_name="Smith",
                tags=["vip"],
            ))
        assert result["data"]["id"] == "cont_abc123"

    def test_list_contacts(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.contacts.list(status="subscribed", limit=25)
        assert "data" in result

    def test_update_contact(self):
        resp = {"data": {"id": "cont_abc123"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.contacts.update(
                "cont_abc123",
                UpdateContactOptions(status="unsubscribed", tags=["churned"]),
            )
        assert result["data"]["id"] == "cont_abc123"

    def test_get_import_job(self):
        resp = {
            "data": {
                "jobId": "imp_abc123",
                "status": "completed",
                "totalRows": 100,
                "processedRows": 98,
                "failedRows": 2,
                "errors": [],
                "completedAt": "2025-01-01T00:01:00Z",
            }
        }
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.contacts.get_import_job("imp_abc123")
        assert result["data"]["status"] == "completed"
        assert result["data"]["processedRows"] == 98


# ── Audiences ────────────────────────────────────────────────────────────────────────────

class TestAudiences:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_audience(self):
        resp = {"data": {"id": "aud_abc123"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 201)):
            result = self.client.audiences.create(CreateAudienceOptions(
                name="Pro users",
                description="All Pro plan users",
                rules=[AudienceRule(field="plan", operator="equals", value="pro")],
            ))
        assert result["data"]["id"] == "aud_abc123"

    def test_list_audiences(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.audiences.list()
        assert "data" in result

    def test_add_contacts_to_audience(self):
        resp = {"data": {"added": 2, "alreadyInAudience": 1, "notFound": 0}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.audiences.add_contacts(
                "aud_abc123", ["cont_1", "cont_2", "cont_3"]
            )
        assert result["data"]["added"] == 2
        assert result["data"]["alreadyInAudience"] == 1


# ── Templates ────────────────────────────────────────────────────────────────────────────

class TestTemplates:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_with_markdown_omits_html(self):
        resp = {"data": {"id": "tmpl_md", "format": "emailmd", "source": "# Hi", "html": "<html>"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as mock_open:
            self.client.templates.create(CreateTemplateOptions(name="md", markdown="# Hi"))
        body = json.loads(mock_open.call_args[0][0].data.decode())
        assert body == {"name": "md", "format": "emailmd", "markdown": "# Hi"}

    def test_update_sends_markdown(self):
        resp = {"data": {"id": "tmpl_md", "version": 2}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as mock_open:
            self.client.templates.update("tmpl_md", UpdateTemplateOptions(markdown="# V2"))
        body = json.loads(mock_open.call_args[0][0].data.decode())
        assert body == {"markdown": "# V2"}

    def test_create_template(self):
        resp = {"data": {"id": "tmpl_abc123", "name": "Welcome", "status": "draft", "version": 1}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 201)):
            result = self.client.templates.create(CreateTemplateOptions(
                name="Welcome", html="<p>Hi {{first_name}}!</p>"
            ))
        assert result["data"]["id"] == "tmpl_abc123"
        assert result["data"]["status"] == "draft"

    def test_update_template(self):
        resp = {"data": {"id": "tmpl_abc123", "version": 2, "status": "published"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.templates.update(
                "tmpl_abc123",
                UpdateTemplateOptions(html="<p>Updated!</p>", status="published"),
            )
        assert result["data"]["version"] == 2

    def test_delete_template(self):
        with patch(PATCH_URLOPEN, return_value=_mock_response({}, 204)):
            self.client.templates.delete("tmpl_abc123")

    def test_list_versions(self):
        resp = {"data": [{"version": 2, "savedAt": "2025-01-02T00:00:00Z"}]}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.templates.list_versions("tmpl_abc123")
        assert result["data"][0]["version"] == 2

    def test_get_version(self):
        resp = {"data": {"version": 1, "html": "<p>v1</p>", "savedAt": "2025-01-01T00:00:00Z"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.templates.get_version("tmpl_abc123", 1)
        assert result["data"]["html"] == "<p>v1</p>"

    def test_test_send(self):
        resp = {"data": {"queued": True}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 202)):
            result = self.client.templates.test_send(
                "tmpl_abc123", "you@example.com", variables={"name": "Test"}
            )
        assert result["data"]["queued"] is True


# ── Domains ─────────────────────────────────────────────────────────────────────────────

class TestDomains:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_add_domain(self):
        resp = {
            "data": {
                "id": "dom_abc123",
                "domain": "acme.com",
                "status": "pending",
                "records": [],
            }
        }
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 201)):
            result = self.client.domains.add("acme.com")
        assert result["data"]["domain"] == "acme.com"
        assert result["data"]["status"] == "pending"

    def test_verify_domain(self):
        resp = {"data": {"id": "dom_abc123", "status": "verified"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.domains.verify("dom_abc123")
        assert result["data"]["status"] == "verified"

    def test_delete_domain(self):
        resp = {"data": {"id": "dom_abc123", "deletedAt": "2025-01-01T00:00:00Z"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.domains.delete("dom_abc123")
        assert result["data"]["id"] == "dom_abc123"


# ── Campaigns ────────────────────────────────────────────────────────────────────────────

class TestCampaigns:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_campaign(self):
        resp = {"data": {"id": "camp_abc123"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 201)):
            result = self.client.campaigns.create(CreateCampaignOptions(
                name="January newsletter",
                template_id="tmpl_abc",
                audience_id="aud_abc",
                from_name="Acme",
                from_email="news@acme.com",
                subject_a="Hello January",
                subject_b="January highlights",
            ))
        assert result["data"]["id"] == "camp_abc123"

    def test_send_campaign_immediately(self):
        resp = {"data": {"status": "sending"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.campaigns.send("camp_abc123")
        assert result["data"]["status"] == "sending"

    def test_schedule_campaign(self):
        resp = {"data": {"status": "scheduled"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.campaigns.send(
                "camp_abc123", scheduled_at="2025-01-20T10:00:00Z"
            )
        assert result["data"]["status"] == "scheduled"

    def test_unschedule_campaign(self):
        resp = {"data": {"id": "camp_abc123", "status": "draft", "scheduledAt": None}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            result = self.client.campaigns.unschedule("camp_abc123")
        assert m.call_args[0][0].full_url.endswith("/v1/campaigns/camp_abc123/unschedule")
        assert result["data"]["status"] == "draft"
        assert result["data"]["scheduledAt"] is None

    def test_unschedule_campaign_already_sending_raises_conflict(self):
        body = {"error": {"code": "CONFLICT", "message": "already started sending"}}
        with patch(PATCH_URLOPEN, side_effect=_http_error(body, 409)):
            with pytest.raises(TrattoError) as e:
                self.client.campaigns.unschedule("camp_abc123")
        assert e.value.code == "CONFLICT"
        assert e.value.status_code == 409

    def test_pause_campaign(self):
        resp = {"data": {"status": "paused"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.campaigns.pause("camp_abc123")
        assert result["data"]["status"] == "paused"

    def test_get_stats(self):
        resp = {
            "data": {
                "campaignId": "camp_abc123",
                "status": "completed",
                "stats": {"total": 1000, "sent": 1000, "delivered": 950,
                           "opened": 300, "clicked": 100, "bounced": 50},
                "rates": {"deliveryRate": 95.0, "openRate": 30.0,
                           "clickRate": 10.0, "bounceRate": 5.0},
            }
        }
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.campaigns.get_stats("camp_abc123")
        assert result["data"]["rates"]["openRate"] == 30.0

    def test_test_send_campaign(self):
        resp = {"data": {"emailId": "email_test123"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.campaigns.test_send("camp_abc123", "you@example.com")
        assert result["data"]["emailId"] == "email_test123"


# ── Webhooks ─────────────────────────────────────────────────────────────────────────────

class TestWebhooks:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_webhook(self):
        resp = {"data": {"id": "wh_abc123", "secret": "whsec_abc"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 201)):
            result = self.client.webhooks.create(CreateWebhookOptions(
                url="https://example.com/webhooks/tratto",
                events=["delivered", "bounced"],
            ))
        assert result["data"]["id"] == "wh_abc123"
        assert "secret" in result["data"]

    def test_list_webhooks(self):
        resp = {"data": []}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.webhooks.list()
        assert "data" in result

    def test_delete_webhook(self):
        with patch(PATCH_URLOPEN, return_value=_mock_response({}, 204)):
            self.client.webhooks.delete("wh_abc123")

    def test_test_webhook(self):
        resp = {"data": {"queued": True}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.webhooks.test("wh_abc123")
        assert result["data"]["queued"] is True

    def test_rotate_secret(self):
        resp = {"data": {"secret": "whsec_newabcdef"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.webhooks.rotate_secret("wh_abc123")
        assert result["data"]["secret"].startswith("whsec_")

    def test_list_deliveries(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.webhooks.list_deliveries("wh_abc123", limit=10)
        assert "data" in result


# ── Analytics ─────────────────────────────────────────────────────────────────────────────

class TestAnalytics:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_summary_defaults_to_30d(self):
        resp = {"data": {"period": "30d", "totalSent": 12}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            result = self.client.analytics.get_summary()
        assert result["data"]["totalSent"] == 12
        assert "period=30d" in m.call_args[0][0].full_url

    def test_summary_honours_an_explicit_period(self):
        resp = {"data": {"period": "7d"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.analytics.get_summary("7d")
        assert "period=7d" in m.call_args[0][0].full_url

    def test_timeseries(self):
        resp = {"data": [{"date": "2026-08-10", "sent": 3}]}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            result = self.client.analytics.get_timeseries("24h")
        assert result["data"][0]["sent"] == 3
        assert "/v1/analytics/timeseries" in m.call_args[0][0].full_url


# ── Flows ─────────────────────────────────────────────────────────────────────────────────

class TestFlows:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_list_passes_status_filter(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.flows.list(status="active", limit=10)
        assert "status=active" in m.call_args[0][0].full_url

    def test_create_returns_the_flow(self):
        resp = {"data": {"id": "flow_abc", "status": "draft"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.flows.create({"name": "Welcome", "steps": []})
        # A new flow starts as a draft — nothing is enrolled until it's activated.
        assert result["data"]["status"] == "draft"

    def test_get(self):
        resp = {"data": {"id": "flow_abc"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.flows.get("flow_abc")
        assert m.call_args[0][0].full_url.endswith("/v1/flows/flow_abc")

    def test_update_uses_patch(self):
        resp = {"data": {"id": "flow_abc", "name": "Renamed"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.flows.update("flow_abc", {"name": "Renamed"})
        assert m.call_args[0][0].get_method() == "PATCH"

    def test_delete(self):
        with patch(PATCH_URLOPEN, return_value=_mock_response({})) as m:
            self.client.flows.delete("flow_abc")
        assert m.call_args[0][0].get_method() == "DELETE"

    def test_activate_and_deactivate_hit_their_endpoints(self):
        resp = {"data": {"id": "flow_abc", "status": "active"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.flows.activate("flow_abc")
        assert m.call_args[0][0].full_url.endswith("/activate")

        resp = {"data": {"id": "flow_abc", "status": "paused"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.flows.deactivate("flow_abc")
        assert m.call_args[0][0].full_url.endswith("/deactivate")


# ── Workspace ─────────────────────────────────────────────────────────────────────────────

class TestWorkspace:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_get(self):
        resp = {"data": {"id": "tenant_abc", "name": "Acme", "plan": "starter"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)):
            result = self.client.workspace.get()
        assert result["data"]["plan"] == "starter"

    def test_update_uses_patch(self):
        resp = {"data": {"id": "tenant_abc", "name": "Renamed"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.workspace.update({"name": "Renamed"})
        assert m.call_args[0][0].get_method() == "PATCH"

    def test_update_senders_sends_only_the_type_given(self):
        """Scrittura parziale (#20): un tipo solo, gli altri due non si toccano."""
        resp = {"data": {"id": "tenant_abc"}}
        body = {"senders": {"marketing": {"fromEmail": "news@acme.test", "fromName": "Acme"}}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.workspace.update(body)
        sent = json.loads(m.call_args[0][0].data.decode())
        assert sent == body
        assert "automation" not in sent["senders"]

    def test_update_senders_keeps_none_instead_of_dropping_it(self):
        """`None` su un tipo lo rimette in eredita': non deve sparire nel JSON."""
        resp = {"data": {"id": "tenant_abc"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.workspace.update({"senders": {"marketing": None}})
        sent = json.loads(m.call_args[0][0].data.decode())
        assert sent == {"senders": {"marketing": None}}

    def test_update_preferences_targets_its_own_endpoint(self):
        resp = {"data": {"language": "it"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.workspace.update_preferences({"language": "it"})
        assert m.call_args[0][0].full_url.endswith("/v1/workspace/preferences")

    def test_invite_member_sends_email_and_role(self):
        resp = {"data": {"userId": "inv_abc", "role": "admin"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.workspace.invite_member("dev@example.com", "admin")
        body = json.loads(m.call_args[0][0].data.decode())
        assert body == {"email": "dev@example.com", "role": "admin"}

    def test_update_member(self):
        resp = {"data": {"userId": "uid_1", "role": "member"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.workspace.update_member("uid_1", "member")
        assert m.call_args[0][0].full_url.endswith("/v1/workspace/members/uid_1")

    def test_remove_member(self):
        with patch(PATCH_URLOPEN, return_value=_mock_response({})) as m:
            self.client.workspace.remove_member("uid_1")
        assert m.call_args[0][0].get_method() == "DELETE"
