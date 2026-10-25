import json
from io import BytesIO
from unittest.mock import patch

import pytest

from tratto import SendEmailOptions, Tratto, TrattoError
from tratto.resources.attachments import content_disposition

from .test_client import PATCH_URLOPEN, _http_error, _mock_response

ATT = {
    "id": "att_123456789012345678901", "filename": "invoice.pdf",
    "contentType": "application/pdf", "size": 3, "sha256": "ab",
    "livemode": False, "expiresAt": "2030-01-01T00:00:00.000Z",
}


@pytest.fixture
def client():
    return Tratto("tratto_test_key")


def test_upload_posts_raw_bytes_with_headers(client):
    with patch(PATCH_URLOPEN, return_value=_mock_response({"data": ATT}, 201)) as m:
        result = client.attachments.upload(
            b"%PD", filename="invoice.pdf", content_type="application/pdf"
        )
    req = m.call_args[0][0]
    assert req.full_url == "https://api.tratto.email/v1/attachments"
    assert req.get_method() == "POST"
    assert req.data == b"%PD"
    assert req.get_header("Content-type") == "application/pdf"
    assert req.get_header("Content-disposition") == 'attachment; filename="invoice.pdf"'
    assert result == ATT


def test_upload_reads_file_object_and_never_json_encodes(client):
    with patch(PATCH_URLOPEN, return_value=_mock_response({"data": ATT}, 201)) as m:
        client.attachments.upload(
            BytesIO(b'{"a":1}'), filename="data.json", content_type="application/json"
        )
    req = m.call_args[0][0]
    assert req.data == b'{"a":1}'
    assert req.get_header("Content-type") == "application/json"


def test_upload_quota_exceeded_raises(client):
    err = {"error": {"code": "QUOTA_EXCEEDED", "message": "storage full"}}
    with (
        patch(PATCH_URLOPEN, side_effect=_http_error(err, 429)),
        pytest.raises(TrattoError) as e,
    ):
        client.attachments.upload(b"\x01", filename="a.bin", content_type="application/octet-stream")
    assert (e.value.status_code, e.value.code) == (429, "QUOTA_EXCEEDED")


def test_get_unwraps_data(client):
    with patch(PATCH_URLOPEN, return_value=_mock_response({"data": ATT})) as m:
        result = client.attachments.get(ATT["id"])
    assert m.call_args[0][0].full_url.endswith(f"/v1/attachments/{ATT['id']}")
    assert result["sha256"] == "ab"


def test_delete_handles_204(client):
    with patch(PATCH_URLOPEN, return_value=_mock_response({}, 204)) as m:
        m.return_value.read.return_value = b""
        assert client.attachments.delete(ATT["id"]) is None
    req = m.call_args[0][0]
    assert req.get_method() == "DELETE"
    assert req.full_url.endswith(f"/v1/attachments/{ATT['id']}")


def test_content_disposition_ascii_escapes_quotes_and_backslashes():
    assert content_disposition('a "b"\\c.pdf') == 'attachment; filename="a \\"b\\"\\\\c.pdf"'


def test_content_disposition_non_ascii_uses_rfc5987():
    assert content_disposition("fattura n°1 (l'ultima).pdf") == (
        "attachment; filename=\"fattura n_1 (l'ultima).pdf\"; "
        "filename*=UTF-8''fattura%20n%C2%B01%20%28l%27ultima%29.pdf"
    )


def test_content_disposition_control_chars_are_percent_encoded():
    assert content_disposition("a\r\nb.pdf") == (
        "attachment; filename=\"a__b.pdf\"; filename*=UTF-8''a%0D%0Ab.pdf"
    )


def test_send_and_batch_carry_attachments(client):
    files = [{"id": "att_1"}]
    with patch(PATCH_URLOPEN, return_value=_mock_response({"data": {"id": "em_1"}}, 202)) as m:
        client.emails.send(SendEmailOptions(to="c@d.com", subject="Hi", html="<p/>", attachments=files))
        client.emails.send_batch([SendEmailOptions(to="a@x.it", subject="A", html="<p/>", attachments=files)])
    send_body, batch_body = (json.loads(c[0][0].data) for c in m.call_args_list)
    assert send_body["attachments"] == files
    assert batch_body["emails"][0]["attachments"] == files


def test_send_plan_upgrade_required_raises(client):
    err = {"error": {"code": "PLAN_UPGRADE_REQUIRED", "message": "Starter plan"}}
    with (
        patch(PATCH_URLOPEN, side_effect=_http_error(err, 403)),
        pytest.raises(TrattoError) as e,
    ):
        client.emails.send(SendEmailOptions(to="c@d.com", subject="Hi", html="<p/>", attachments=[{"id": "att_1"}]))
    assert (e.value.status_code, e.value.code) == (403, "PLAN_UPGRADE_REQUIRED")
