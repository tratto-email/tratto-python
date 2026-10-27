import dataclasses
import json
import warnings
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

import tratto.types
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

# 2.0.0: every option class is keyword-only, so a required field can later
# become optional without another major (#19).
OPTION_CLASSES = {
    SendEmailOptions,
    CreateContactOptions,
    UpdateContactOptions,
    AudienceRule,
    CreateAudienceOptions,
    CreateTemplateOptions,
    UpdateTemplateOptions,
    CreateCampaignOptions,
    CreateWebhookOptions,
}


def test_option_classes_cover_every_dataclass():
    assert OPTION_CLASSES == {
        c
        for c in vars(tratto.types).values()
        if isinstance(c, type) and dataclasses.is_dataclass(c)
    }


@pytest.mark.parametrize(
    "cls", sorted(OPTION_CLASSES, key=lambda c: c.__name__), ids=lambda c: c.__name__
)
def test_option_classes_are_keyword_only(cls):
    # As many args as required fields (at least one): without kw_only the
    # positional call would succeed, so TypeError can only come from kw_only.
    names = [
        f.name
        for f in dataclasses.fields(cls)
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
    ] or [dataclasses.fields(cls)[0].name]
    cls(**{n: "x" for n in names})
    with pytest.raises(TypeError):
        cls(*["x"] * len(names))


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
        assert client.attachments is not None

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

    def test_cancel_sends_delete_and_returns_none(self):
        with patch(PATCH_URLOPEN, return_value=_mock_response({}, status=204)) as m:
            assert self.client.emails.cancel("email_a/b") is None
        req = m.call_args[0][0]
        assert req.get_method() == "DELETE"
        assert req.full_url == "https://api.tratto.email/v1/emails/email_a%2Fb"
        assert req.data is None

    def test_cancel_conflict_raises(self):
        body = {"error": {"code": "CONFLICT", "message": "Only scheduled emails can be canceled."}}
        with (
            patch(PATCH_URLOPEN, side_effect=_http_error(body, 409)),
            pytest.raises(TrattoError) as e,
        ):
            self.client.emails.cancel("email_abc")
        assert (e.value.code, e.value.status_code) == ("CONFLICT", 409)

    def test_reschedule_sends_patch_with_scheduled_at(self):
        resp = {"data": {"id": "email_abc", "scheduledAt": "2030-01-20T09:00:00.000Z"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            result = self.client.emails.reschedule("email_abc", "2030-01-20T09:00:00Z")
        req = m.call_args[0][0]
        assert req.get_method() == "PATCH"
        assert req.full_url == "https://api.tratto.email/v1/emails/email_abc"
        assert json.loads(req.data.decode()) == {"scheduledAt": "2030-01-20T09:00:00Z"}
        assert result == resp

    @pytest.mark.parametrize("code", ["QUOTA_EXCEEDED", "RATE_LIMITED"])
    def test_reschedule_429_raises_with_its_code(self, code):
        body = {"error": {"code": code, "message": "Too many."}}
        with (
            patch(PATCH_URLOPEN, side_effect=_http_error(body, 429)),
            pytest.raises(TrattoError) as e,
        ):
            self.client.emails.reschedule("email_abc", "2030-01-20T09:00:00Z")
        assert (e.value.code, e.value.status_code) == (code, 429)

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

    def test_send_without_from_omits_from_key(self):
        resp = {"data": {"id": "email_nofrom"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as mock_open:
            self.client.emails.send(SendEmailOptions(
                to="user@example.com",
                subject="Hello",
                html="<p>Hello</p>",
            ))
        body = json.loads(mock_open.call_args[0][0].data.decode())
        assert "from" not in body
        assert body == {"to": "user@example.com", "subject": "Hello", "html": "<p>Hello</p>"}

    def test_send_with_from_puts_it_in_body(self):
        resp = {"data": {"id": "email_from"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as mock_open:
            self.client.emails.send(SendEmailOptions(
                from_="Acme <hello@acme.com>",
                to="user@example.com",
                subject="Hello",
                html="<p>Hello</p>",
            ))
        body = json.loads(mock_open.call_args[0][0].data.decode())
        assert body["from"] == "Acme <hello@acme.com>"

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

    def test_send_batch_body_header_and_unwrap(self):
        resp = {"data": {"batchId": "batch_1", "livemode": False, "accepted": 2, "failed": 0,
                         "emails": [{"id": "email_1", "status": "queued", "to": ["a@x.it"]},
                                    {"id": "email_2", "status": "queued", "to": ["b@x.it"]}]}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 202)) as mock_open:
            result = self.client.emails.send_batch(
                [
                    SendEmailOptions(to="a@x.it", subject="A", html="<p>A</p>", reply_to="r@x.it"),
                    SendEmailOptions(from_="s@x.it", to=["b@x.it"], subject="B",
                                     template_id="tmpl_1", variables={"n": 1}),
                ],
                idempotency_key="batch-key-1",
            )
        req = mock_open.call_args[0][0]
        assert req.full_url.endswith("/v1/emails/batch")
        assert req.get_method() == "POST"
        assert req.get_header("Idempotency-key") == "batch-key-1"
        assert json.loads(req.data.decode()) == {"emails": [
            {"to": "a@x.it", "subject": "A", "html": "<p>A</p>", "replyTo": "r@x.it"},
            {"from": "s@x.it", "to": ["b@x.it"], "subject": "B",
             "templateId": "tmpl_1", "variables": {"n": 1}},
        ]}
        assert result["accepted"] == 2
        assert [e["id"] for e in result["emails"]] == ["email_1", "email_2"]

    def test_send_batch_partial_failure_returns_instead_of_raising(self):
        resp = {"data": {"batchId": "batch_2", "livemode": True, "accepted": 1, "failed": 1,
                         "emails": [
                             {"id": "email_1", "status": "queued", "to": ["a@x.it"]},
                             {"status": "failed", "to": ["b@x.it"],
                              "error": {"code": "SERVICE_UNAVAILABLE", "message": "retry"}},
                         ]}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp, 202)):
            result = self.client.emails.send_batch([
                SendEmailOptions(to="a@x.it", subject="A", text="A"),
                SendEmailOptions(to="b@x.it", subject="B", text="B"),
            ])
        assert result["failed"] == 1
        failed = [e for e in result["emails"] if e["status"] == "failed"]
        assert failed[0]["to"] == ["b@x.it"]
        assert failed[0]["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "id" not in failed[0]

    def test_send_batch_rejects_item_idempotency_key_without_network(self):
        with (
            patch(PATCH_URLOPEN) as mock_open,
            pytest.raises(ValueError, match=r"send_batch\(\.\.\., idempotency_key"),
        ):
            self.client.emails.send_batch([
                SendEmailOptions(to="a@x.it", subject="A", text="A", idempotency_key="k"),
            ])
        mock_open.assert_not_called()

    def test_send_batch_scheduled_at_goes_to_api(self):
        err = {"error": {"code": "VALIDATION_ERROR", "message": "invalid",
                         "details": [{"path": "/emails/0/scheduledAt", "message": "not allowed"}]}}
        with (
            patch(PATCH_URLOPEN, side_effect=_http_error(err, 422)) as mock_open,
            pytest.raises(TrattoError) as exc_info,
        ):
            self.client.emails.send_batch([
                SendEmailOptions(to="a@x.it", subject="A", text="A",
                                 scheduled_at="2030-01-01T00:00:00Z"),
            ])
        body = json.loads(mock_open.call_args[0][0].data.decode())
        assert body["emails"][0]["scheduledAt"] == "2030-01-01T00:00:00Z"
        assert exc_info.value.status_code == 422
        assert exc_info.value.details is not None
        assert exc_info.value.details[0]["path"] == "/emails/0/scheduledAt"

    def test_send_batch_503_raises(self):
        err = {"error": {"code": "SERVICE_UNAVAILABLE", "message": "try again"}}
        with (
            patch(PATCH_URLOPEN, side_effect=_http_error(err, 503)),
            pytest.raises(TrattoError) as exc_info,
        ):
            self.client.emails.send_batch([SendEmailOptions(to="a@x.it", subject="A", text="A")])
        assert exc_info.value.status_code == 503
        assert exc_info.value.code == "SERVICE_UNAVAILABLE"
        assert exc_info.value.details is None

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
        with (
            patch(PATCH_URLOPEN, side_effect=_http_error(body, 409)),
            pytest.raises(TrattoError) as e,
        ):
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

    def test_list_status_is_deprecated(self):
        # The API list route accepts only after/limit: status is ignored there.
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with (
            patch(PATCH_URLOPEN, return_value=_mock_response(resp)),
            pytest.warns(DeprecationWarning, match="ignores it"),
        ):
            self.client.flows.list(status="active", limit=10)

    def test_list_without_status_does_not_warn(self):
        resp = {"data": [], "pagination": {"hasMore": False, "nextCursor": None}}
        with (
            patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m,
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("error")
            self.client.flows.list(limit=10)
        assert "limit=10" in m.call_args[0][0].full_url

    def test_list_docstring_uses_api_status_enum(self):
        doc = self.client.flows.list.__doc__ or ""
        assert "paused" not in doc
        assert "inactive" in doc

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
        """Partial write (#20): only one type is sent, the other two are left untouched."""
        resp = {"data": {"id": "tenant_abc"}}
        body = {"senders": {"marketing": {"fromEmail": "news@acme.test", "fromName": "Acme"}}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.workspace.update(body)
        sent = json.loads(m.call_args[0][0].data.decode())
        assert sent == body
        assert "automation" not in sent["senders"]

    def test_update_senders_keeps_none_instead_of_dropping_it(self):
        """`None` on a type puts it back to inheriting the default: it must not vanish from the JSON."""
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

    def test_delete_is_deprecated(self):
        with (
            patch(PATCH_URLOPEN, return_value=_mock_response({}, status=204)),
            pytest.warns(DeprecationWarning, match="dashboard"),
        ):
            self.client.workspace.delete()

    def test_invite_member_is_deprecated(self):
        resp = {"data": {"userId": "inv_abc", "role": "admin"}}
        with (
            patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m,
            pytest.warns(DeprecationWarning, match="dashboard"),
        ):
            self.client.workspace.invite_member("dev@example.com", "admin")
        body = json.loads(m.call_args[0][0].data.decode())
        assert body == {"email": "dev@example.com", "role": "admin"}

    def test_update_member(self):
        resp = {"data": {"userId": "uid_1", "role": "member"}}
        with patch(PATCH_URLOPEN, return_value=_mock_response(resp)) as m:
            self.client.workspace.update_member("uid_1", "member")
        assert m.call_args[0][0].full_url.endswith("/v1/workspace/members/uid_1")

    def test_remove_member_is_deprecated(self):
        with (
            patch(PATCH_URLOPEN, return_value=_mock_response({})) as m,
            pytest.warns(DeprecationWarning, match="dashboard"),
        ):
            self.client.workspace.remove_member("uid_1")
        assert m.call_args[0][0].get_method() == "DELETE"


# ── Error payload: suggestion + docs (#24) ───────────────────────────────────────────────

class TestErrorFields:
    """`suggestion` and `docs` reach the integrator, on both HTTP paths."""

    def setup_method(self):
        self.client = Tratto("tratto_live_test")

    def test_json_path_exposes_suggestion_and_docs(self):
        body = {
            "error": {
                "code": "CONFLICT",
                "message": "Campaign is paused while its bounce rate is checked.",
                "suggestion": "Wait for the probe window to expire, then send again.",
                "docs": "https://docs.tratto.email/errors",
            }
        }
        with (
            patch(PATCH_URLOPEN, side_effect=_http_error(body, 409)),
            pytest.raises(TrattoError) as e,
        ):
            self.client.campaigns.send("camp_abc123")
        # No assertion on `message`: that is the point of the issue.
        assert e.value.suggestion == "Wait for the probe window to expire, then send again."
        assert e.value.docs == "https://docs.tratto.email/errors"

    def test_raw_path_exposes_suggestion_and_docs(self):
        # contacts.import_csv goes through _request_raw: the other path that builds the error.
        body = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "suggestion": "The CSV needs an `email` column.",
                "docs": "https://docs.tratto.email/errors",
            }
        }
        with (
            patch(PATCH_URLOPEN, side_effect=_http_error(body, 422)),
            pytest.raises(TrattoError) as e,
        ):
            self.client.contacts.import_csv("name\nalice")
        assert e.value.suggestion == "The CSV needs an `email` column."
        assert e.value.docs == "https://docs.tratto.email/errors"

    def test_missing_fields_are_none_not_empty_string(self):
        # The third 409 of unschedule carries neither suggestion nor docs.
        body = {"error": {"code": "CONFLICT", "message": "Campaign is not scheduled."}}
        with (
            patch(PATCH_URLOPEN, side_effect=_http_error(body, 409)),
            pytest.raises(TrattoError) as e,
        ):
            self.client.campaigns.unschedule("camp_abc123")
        assert e.value.suggestion is None
        assert e.value.docs is None

    def test_three_positional_args_still_build(self):
        # Backward compatibility: code that builds it in its own tests needs no change.
        err = TrattoError("boom", "CONFLICT", 409)
        assert (err.code, err.status_code, err.suggestion, err.docs) == ("CONFLICT", 409, None, None)


# ── Path encoding (#46) ───────────────────────────────────────────────────────────────────

class TestPathEncoding:
    @pytest.mark.parametrize(
        "call, expected",
        [
            (lambda c: c.emails.get("a/b?c#d"), "/v1/emails/a%2Fb%3Fc%23d"),
            (lambda c: c.domains.verify("../x"), "/v1/domains/..%2Fx/verify"),
            (
                lambda c: c.templates.get_version("t/1", 2),
                "/v1/templates/t%2F1/versions/2",
            ),
            (
                lambda c: c.workspace.update_member("u 1", "admin"),
                "/v1/workspace/members/u%201",
            ),
            (lambda c: c.webhooks.test("w#1"), "/v1/webhooks/w%231/test"),
        ],
    )
    def test_ids_are_encoded_as_one_segment(self, call, expected):
        with patch(PATCH_URLOPEN, return_value=_mock_response({"data": {}})) as mock_open:
            call(Tratto("tratto_live_test", base_url="https://api.test"))
        assert mock_open.call_args[0][0].full_url == f"https://api.test{expected}"


# ── Timeout (#37) ─────────────────────────────────────────────────────────────────────────

class TestTimeout:
    def test_default_timeout_is_60_seconds(self):
        with patch(PATCH_URLOPEN, return_value=_mock_response({"data": {}})) as mock_open:
            Tratto("tratto_live_test").workspace.get()
        assert mock_open.call_args.kwargs["timeout"] == 60

    def test_timeout_option_is_passed_to_every_request(self):
        client = Tratto("tratto_live_test", timeout=5)
        with patch(PATCH_URLOPEN, return_value=_mock_response({"data": {}})) as mock_open:
            client.workspace.get()
            client.attachments.upload(b"x", filename="a.txt", content_type="text/plain")
        assert [c.kwargs["timeout"] for c in mock_open.call_args_list] == [5, 5]

    def test_rejects_non_positive_timeout(self):
        with pytest.raises(ValueError):
            Tratto("tratto_live_test", timeout=0)

    @pytest.mark.parametrize(
        "exc", [TimeoutError("timed out"), URLError(TimeoutError("timed out"))]
    )
    def test_timeout_raises_tratto_error(self, exc):
        client = Tratto("tratto_live_test", timeout=5)
        with patch(PATCH_URLOPEN, side_effect=exc), pytest.raises(TrattoError) as info:
            client.emails.get("e1")
        assert info.value.code == "timeout"
        assert info.value.status_code == 0

    def test_other_network_errors_are_not_reported_as_timeout(self):
        client = Tratto("tratto_live_test")
        dns = URLError("Name or service not known")
        with patch(PATCH_URLOPEN, side_effect=dns), pytest.raises(URLError):
            client.emails.get("e1")
