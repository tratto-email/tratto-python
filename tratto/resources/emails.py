
from .._http import HttpClient, _seg
from ..types import SendBatchResult, SendEmailOptions


def _email_body(options: SendEmailOptions) -> dict:
    """Map one :class:`SendEmailOptions` to its JSON body (shared by send and send_batch)."""
    body: dict = {
        "to": options.to,
        "subject": options.subject,
    }
    if options.from_ is not None:
        body["from"] = options.from_
    if options.html is not None:
        body["html"] = options.html
    if options.markdown is not None:
        body["markdown"] = options.markdown
    if options.text is not None:
        body["text"] = options.text
    if options.reply_to is not None:
        body["replyTo"] = options.reply_to
    if options.cc is not None:
        body["cc"] = options.cc
    if options.bcc is not None:
        body["bcc"] = options.bcc
    if options.headers is not None:
        body["headers"] = options.headers
    if options.tags is not None:
        body["tags"] = options.tags
    if options.template_id is not None:
        body["templateId"] = options.template_id
    if options.variables is not None:
        body["variables"] = options.variables
    if options.attachments is not None:
        body["attachments"] = options.attachments
    if options.scheduled_at is not None:
        body["scheduledAt"] = options.scheduled_at
    return body


class EmailsResource:
    """Methods for the ``/v1/emails`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def send(self, options: SendEmailOptions) -> dict:
        """Send a transactional email.

        Returns ``{"id": "<email_id>"}`` on success (HTTP 202).
        Raises :class:`~tratto.TrattoError` on failure.

        Example::

            result = client.emails.send(SendEmailOptions(
                from_="hello@yourdomain.com",
                to="user@example.com",
                subject="Welcome!",
                html="<p>Welcome to our platform.</p>",
            ))
            print(result["id"])  # email_…
        """
        body = _email_body(options)

        extra_headers: dict[str, str] = {}
        if options.idempotency_key:
            extra_headers["Idempotency-Key"] = options.idempotency_key

        result = self._http._request(
            "POST", "/v1/emails", body=body, extra_headers=extra_headers
        )
        return result.get("data", result)

    def send_batch(
        self, emails: list[SendEmailOptions], *, idempotency_key: str | None = None
    ) -> SendBatchResult:
        """Send up to 100 transactional emails in one request.

        Each item takes the same options as :meth:`send`. ``scheduled_at`` is
        not supported in a batch (the API answers 422 with the item's path in
        ``TrattoError.details``), and the idempotency key covers the whole
        batch: pass it here, not on the items.

        Always returns the 202 payload, also when some items failed: check
        ``result["failed"]`` and resend only the items with
        ``status == "failed"`` in a new batch with a **new** key. After a 503
        or 500 nothing was sent and retrying with the **same** key is safe.

        Raises :class:`~tratto.TrattoError` on any non-2xx response, and
        ``ValueError`` if an item carries its own ``idempotency_key``.

        Example::

            result = client.emails.send_batch(
                [SendEmailOptions(to="a@example.com", subject="Hi", html="<p>Hi</p>")],
                idempotency_key=str(uuid.uuid4()),
            )
            retry = [e for e in result["emails"] if e["status"] == "failed"]
        """
        for i, options in enumerate(emails):
            if options.idempotency_key:
                raise ValueError(
                    f"emails[{i}].idempotency_key is not supported in a batch: the key covers "
                    "the whole batch, pass it as send_batch(..., idempotency_key=...)"
                )

        extra_headers: dict[str, str] = {}
        if idempotency_key:
            extra_headers["Idempotency-Key"] = idempotency_key

        result = self._http._request(
            "POST",
            "/v1/emails/batch",
            body={"emails": [_email_body(o) for o in emails]},
            extra_headers=extra_headers,
        )
        data: SendBatchResult = result.get("data", result)
        return data

    def list(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        after: str | None = None,
        domain_id: str | None = None,
        tags: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """List emails with optional filters.

        Returns a paginated response::

            {
                "data": [...],
                "pagination": {"hasMore": bool, "nextCursor": str | None}
            }

        Use ``after=response["pagination"]["nextCursor"]`` to fetch the next page.

        Args:
            status: Filter by status. Accepts a comma-separated list
                (e.g. ``"delivered,opened"``) or a single value.
            limit: Results per page (1–100, default 50).
            after: Cursor from the previous page's ``nextCursor``.
            domain_id: Filter by sender domain ID.
            tags: Comma-separated list of tags to filter by.
            date_from: ISO-8601 datetime lower bound (inclusive).
            date_to: ISO-8601 datetime upper bound (inclusive).
        """
        return self._http._request(
            "GET",
            "/v1/emails",
            params={
                "status": status,
                "limit": limit,
                "after": after,
                "domainId": domain_id,
                "tags": tags,
                "dateFrom": date_from,
                "dateTo": date_to,
            },
        )

    def get(self, email_id: str) -> dict:
        """Get full details for a single email, including inline delivery events.

        ``data["attachments"]`` lists the files sent with it
        (:class:`~tratto.EmailAttachment`). A failed email carries
        ``data["failureReason"]`` (e.g. ``"template_not_found"`` or
        ``"attachment_unavailable"``), the same code as ``reason`` of the
        ``failed`` webhook event; absent on emails that failed before the
        field existed. The set is open: handle unknown values.
        """
        return self._http._request("GET", f"/v1/emails/{_seg(email_id)}")

    def get_events(self, email_id: str) -> dict:
        """List all delivery events for an email.

        Returns events in chronological order::

            {
                "data": [
                    {"type": "sent", "occurredAt": "2025-01-01T00:00:00Z"},
                    {"type": "delivered", "occurredAt": "2025-01-01T00:00:05Z"},
                    ...
                ]
            }

        Event types: ``sent``, ``delivered``, ``opened``, ``clicked``,
        ``bounced``, ``complained``, ``unsubscribed``.
        """
        return self._http._request("GET", f"/v1/emails/{_seg(email_id)}/events")

    def cancel(self, email_id: str) -> None:
        """Cancel an email still in *scheduled* status.

        The email goes to *canceled* and is never sent; its emails (one per
        distinct recipient) go back to the quota of the month it was booked
        on. Requires tratto-email 2.3.0 or later.

        Raises:
            TrattoError: ``CONFLICT`` (409) if the email is no longer
                *scheduled* (already queued, sent or canceled);
                ``NOT_FOUND`` (404); ``RATE_LIMITED`` (429) under contention
                on the account quota, safe to retry.
        """
        self._http._request("DELETE", f"/v1/emails/{_seg(email_id)}")

    def reschedule(self, email_id: str, scheduled_at: str) -> dict:
        """Move a *scheduled* email to a new ISO-8601 date in the future.

        Returns ``{"data": {"id": str, "scheduledAt": str}}``. Requires
        tratto-email 2.3.0 or later.

        Moving it to another UTC month moves its quota emails to that month.

        Raises:
            TrattoError: ``CONFLICT`` (409) if the email is no longer
                *scheduled*; ``VALIDATION_ERROR`` (422) if *scheduled_at* is
                not in the future, or an attachment would expire less than an
                hour after it or was deleted; ``QUOTA_EXCEEDED`` (429) if the
                target month has fewer emails left than the email has
                recipients; ``RATE_LIMITED`` (429) under contention, safe to
                retry; ``NOT_FOUND`` (404).
        """
        return self._http._request(
            "PATCH",
            f"/v1/emails/{_seg(email_id)}",
            body={"scheduledAt": scheduled_at},
        )
