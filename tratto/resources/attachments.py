import re
from typing import BinaryIO
from urllib.parse import quote

from .._http import HttpClient, _seg
from ..types import Attachment


def content_disposition(filename: str) -> str:
    """``Content-Disposition`` for *filename* (RFC 6266 / RFC 5987).

    Printable ASCII goes in a quoted ``filename``; anything else also gets
    ``filename*=UTF-8''…`` with an ASCII fallback, because header values must
    be ASCII.
    """

    def quoted(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    if re.fullmatch(r"[\x20-\x7e]*", filename):
        return f"attachment; filename={quoted(filename)}"
    fallback = re.sub(r"[^\x20-\x7e]", "_", filename)
    return f"attachment; filename={quoted(fallback)}; filename*=UTF-8''{quote(filename, safe='')}"


class AttachmentsResource:
    """Methods for the ``/v1/attachments`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def upload(
        self, content: bytes | BinaryIO, *, filename: str, content_type: str
    ) -> Attachment:
        """Upload a file (raw bytes) and return its metadata.

        Reference it from ``emails.send`` or ``emails.send_batch`` with
        ``attachments=[{"id": attachment["id"]}]``. The bytes are sent as they
        are, also when *content_type* is ``application/json``.

        Not available on the Free plan (403 ``PLAN_UPGRADE_REQUIRED``); a full
        workspace storage answers 429 ``QUOTA_EXCEEDED``.

        Example::

            with open("invoice.pdf", "rb") as f:
                att = client.attachments.upload(
                    f, filename="invoice.pdf", content_type="application/pdf"
                )
        """
        body = content if isinstance(content, bytes) else content.read()
        result = self._http._request_raw(
            "POST",
            "/v1/attachments",
            body=body,
            content_type=content_type,
            extra_headers={"Content-Disposition": content_disposition(filename)},
        )
        data: Attachment = result.get("data", result)
        return data

    def get(self, attachment_id: str) -> Attachment:
        """Get an attachment's metadata. The bytes are never served back."""
        result = self._http._request("GET", f"/v1/attachments/{_seg(attachment_id)}")
        data: Attachment = result.get("data", result)
        return data

    def delete(self, attachment_id: str) -> None:
        """Delete an attachment and free its storage at once.

        Emails already queued with it fail with
        ``failureReason == "attachment_unavailable"``.
        """
        self._http._request("DELETE", f"/v1/attachments/{_seg(attachment_id)}")
