from typing import Optional

from .._http import HttpClient
from ..types import SendEmailOptions


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
        body: dict = {
            "from": options.from_,
            "to": options.to,
            "subject": options.subject,
        }
        if options.html is not None:
            body["html"] = options.html
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
        if options.scheduled_at is not None:
            body["scheduledAt"] = options.scheduled_at

        extra_headers: dict[str, str] = {}
        if options.idempotency_key:
            extra_headers["Idempotency-Key"] = options.idempotency_key

        result = self._http._request(
            "POST", "/v1/emails", body=body, extra_headers=extra_headers
        )
        return result.get("data", result)

    def list(
        self,
        *,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        domain_id: Optional[str] = None,
        tags: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
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
        """Get full details for a single email, including inline delivery events."""
        return self._http._request("GET", f"/v1/emails/{email_id}")

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
        return self._http._request("GET", f"/v1/emails/{email_id}/events")
