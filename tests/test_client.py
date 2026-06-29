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


# ── Helpers ───────────────────────────────────────────────────────────────────

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


# ── Client init ───────────────────────────────────────────────────────────────

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


# ── Emails ────────────────────────────────────────────────────────────────────

class TestEmails:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_send_email_returns_id(self):
        resp = {"data": {"id": "email_abc123"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.emails.send(SendEmailOptions(
                from_="sender@example.com",
                to="user@example.com",
                subject="Hello",
                html="<p>Hello</p>",
            ))
        assert result["id"] == "email_abc123"

    def test_send_with_template(self):
        resp = {"data": {"id": "email_abc123"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
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
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)) as mock_open:
            self.client.emails.send(SendEmailOptions(
                from_="sender@example.com",
                to="user@example.com",
                subject="Hello",
                html="<p>Hello</p>",
                idempotency_key="idem-key-123",
            ))
        req = mock_open.call_args[0][0]
        assert req.get_header("Idempotency-key") == "idem-key-123"

    def test_list_emails(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.emails.list(status="delivered", limit=10)
        assert "data" in result
        assert "pagination" in result

    def test_get_email(self):
        resp = {"data": {"id": "email_abc123", "status": "delivered", "events": []}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.emails.get("email_abc123")
        assert result["data"]["id"] == "email_abc123"

    def test_get_events(self):
        resp = {"data": [{"type": "delivered", "occurredAt": "2025-01-01T00:00:00Z"}]}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.emails.get_events("email_abc123")
        assert result["data"][0]["type"] == "delivered"

    def test_api_error_raises_tratto_error(self):
        error = _http_error({"error": {"code": "NOT_FOUND", "message": "Email not found"}}, 404)
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(TrattoError) as exc_info:
                self.client.emails.get("email_notexist")
        assert exc_info.value.code == "NOT_FOUND"
        assert exc_info.value.status_code == 404
        assert "Email not found" in str(exc_info.value)

    def test_unauthorized_raises_tratto_error(self):
        error = _http_error({"error": {"code": "UNAUTHORIZED", "message": "Invalid API key"}}, 401)
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(TrattoError) as exc_info:
                self.client.emails.list()
        assert exc_info.value.status_code == 401


# ── Contacts ──────────────────────────────────────────────────────────────────

class TestContacts:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_contact(self):
        resp = {"data": {"id": "cont_abc123"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp, 201)):
            result = self.client.contacts.create(CreateContactOptions(
                email="alice@example.com",
                first_name="Alice",
                last_name="Smith",
                tags=["vip"],
            ))
        assert result["data"]["id"] == "cont_abc123"

    def test_list_contacts(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.contacts.list(status="subscribed", limit=25)
        assert "data" in result

    def test_update_contact(self):
        resp = {"data": {"id": "cont_abc123"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
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
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.contacts.get_import_job("imp_abc123")
        assert result["data"]["status"] == "completed"
        assert result["data"]["processedRows"] == 98


# ── Audiences ─────────────────────────────────────────────────────────────────

class TestAudiences:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_audience(self):
        resp = {"data": {"id": "aud_abc123"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp, 201)):
            result = self.client.audiences.create(CreateAudienceOptions(
                name="Pro users",
                description="All Pro plan users",
                rules=[AudienceRule(field="plan", operator="equals", value="pro")],
            ))
        assert result["data"]["id"] == "aud_abc123"

    def test_list_audiences(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.audiences.list()
        assert "data" in result

    def test_add_contacts_to_audience(self):
        resp = {"data": {"added": 2, "alreadyInAudience": 1, "notFound": 0}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.audiences.add_contacts(
                "aud_abc123", ["cont_1", "cont_2", "cont_3"]
            )
        assert result["data"]["added"] == 2
        assert result["data"]["alreadyInAudience"] == 1


# ── Templates ─────────────────────────────────────────────────────────────────

class TestTemplates:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_template(self):
        resp = {"data": {"id": "tmpl_abc123", "name": "Welcome", "status": "draft", "version": 1}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp, 201)):
            result = self.client.templates.create(CreateTemplateOptions(
                name="Welcome", html="<p>Hi {{first_name}}!</p>"
            ))
        assert result["data"]["id"] == "tmpl_abc123"
        assert result["data"]["status"] == "draft"

    def test_update_template(self):
        resp = {"data": {"id": "tmpl_abc123", "version": 2, "status": "published"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.templates.update(
                "tmpl_abc123",
                UpdateTemplateOptions(html="<p>Updated!</p>", status="published"),
            )
        assert result["data"]["version"] == 2

    def test_delete_template(self):
        with patch("urllib.request.urlopen", return_value=_mock_response({}, 204)):
            self.client.templates.delete("tmpl_abc123")

    def test_list_versions(self):
        resp = {"data": [{"version": 2, "savedAt": "2025-01-02T00:00:00Z"}]}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.templates.list_versions("tmpl_abc123")
        assert result["data"][0]["version"] == 2

    def test_get_version(self):
        resp = {"data": {"version": 1, "html": "<p>v1</p>", "savedAt": "2025-01-01T00:00:00Z"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.templates.get_version("tmpl_abc123", 1)
        assert result["data"]["html"] == "<p>v1</p>"

    def test_test_send(self):
        resp = {"data": {"queued": True}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp, 202)):
            result = self.client.templates.test_send(
                "tmpl_abc123", "you@example.com", variables={"name": "Test"}
            )
        assert result["data"]["queued"] is True


# ── Domains ───────────────────────────────────────────────────────────────────

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
        with patch("urllib.request.urlopen", return_value=_mock_response(resp, 201)):
            result = self.client.domains.add("acme.com")
        assert result["data"]["domain"] == "acme.com"
        assert result["data"]["status"] == "pending"

    def test_verify_domain(self):
        resp = {"data": {"id": "dom_abc123", "status": "verified"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.domains.verify("dom_abc123")
        assert result["data"]["status"] == "verified"

    def test_delete_domain(self):
        resp = {"data": {"id": "dom_abc123", "deletedAt": "2025-01-01T00:00:00Z"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.domains.delete("dom_abc123")
        assert result["data"]["id"] == "dom_abc123"


# ── Campaigns ─────────────────────────────────────────────────────────────────

class TestCampaigns:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_campaign(self):
        resp = {"data": {"id": "camp_abc123"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp, 201)):
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
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.campaigns.send("camp_abc123")
        assert result["data"]["status"] == "sending"

    def test_schedule_campaign(self):
        resp = {"data": {"status": "scheduled"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.campaigns.send(
                "camp_abc123", scheduled_at="2025-01-20T10:00:00Z"
            )
        assert result["data"]["status"] == "scheduled"

    def test_pause_campaign(self):
        resp = {"data": {"status": "paused"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
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
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.campaigns.get_stats("camp_abc123")
        assert result["data"]["rates"]["openRate"] == 30.0

    def test_test_send_campaign(self):
        resp = {"data": {"emailId": "email_test123"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.campaigns.test_send("camp_abc123", "you@example.com")
        assert result["data"]["emailId"] == "email_test123"


# ── Webhooks ──────────────────────────────────────────────────────────────────

class TestWebhooks:
    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_create_webhook(self):
        resp = {"data": {"id": "wh_abc123", "secret": "whsec_abc"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp, 201)):
            result = self.client.webhooks.create(CreateWebhookOptions(
                url="https://example.com/webhooks/tratto",
                events=["delivered", "bounced"],
            ))
        assert result["data"]["id"] == "wh_abc123"
        assert "secret" in result["data"]

    def test_list_webhooks(self):
        resp = {"data": []}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.webhooks.list()
        assert "data" in result

    def test_delete_webhook(self):
        with patch("urllib.request.urlopen", return_value=_mock_response({}, 204)):
            self.client.webhooks.delete("wh_abc123")

    def test_test_webhook(self):
        resp = {"data": {"queued": True}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.webhooks.test("wh_abc123")
        assert result["data"]["queued"] is True

    def test_rotate_secret(self):
        resp = {"data": {"secret": "whsec_newabcdef"}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.webhooks.rotate_secret("wh_abc123")
        assert result["data"]["secret"].startswith("whsec_")

    def test_list_deliveries(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = self.client.webhooks.list_deliveries("wh_abc123", limit=10)
        assert "data" in result
