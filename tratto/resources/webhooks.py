from typing import Optional

from .._http import HttpClient
from ..types import CreateWebhookOptions


class WebhooksResource:
    """Methods for the ``/v1/webhooks`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(self, options: CreateWebhookOptions) -> dict:
        """Register a webhook endpoint.

        Returns ``{"data": {"id": str, "secret": str}}`` (HTTP 201).

        **Important:** store the ``secret`` securely — it is only returned
        once and is used to verify webhook signatures.
        """
        return self._http._request(
            "POST",
            "/v1/webhooks",
            body={"url": options.url, "events": options.events},
        )

    def list(self) -> dict:
        """List all registered webhooks.

        Returns ``{"data": [...]}`` with id, url, events, status, and
        failureCount for each webhook.
        """
        return self._http._request("GET", "/v1/webhooks")

    def delete(self, webhook_id: str) -> None:
        """Delete a webhook."""
        self._http._request("DELETE", f"/v1/webhooks/{webhook_id}")

    def list_deliveries(
        self,
        webhook_id: str,
        *,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> dict:
        """List delivery history for a webhook (most recent first).

        Returns a paginated list of delivery attempts with HTTP status,
        response body, and retry count for each attempt.
        """
        return self._http._request(
            "GET",
            f"/v1/webhooks/{webhook_id}/deliveries",
            params={"limit": limit, "after": after},
        )

    def test(self, webhook_id: str) -> dict:
        """Send a synthetic *delivered* test event to a webhook.

        Useful for verifying your endpoint is reachable and your signature
        verification code is correct.

        Returns ``{"data": {"queued": True}}``.
        """
        return self._http._request("POST", f"/v1/webhooks/{webhook_id}/test")

    def rotate_secret(self, webhook_id: str) -> dict:
        """Rotate the signing secret for a webhook.

        Returns ``{"data": {"secret": str}}`` with the new secret.
        Update your server immediately — deliveries signed with the old secret
        will fail verification.
        """
        return self._http._request(
            "POST", f"/v1/webhooks/{webhook_id}/rotate-secret"
        )
