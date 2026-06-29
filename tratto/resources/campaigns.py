from typing import Optional

from .._http import HttpClient
from ..types import CreateCampaignOptions


class CampaignsResource:
    """Methods for the ``/v1/campaigns`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(self, options: CreateCampaignOptions) -> dict:
        """Create a campaign in *draft* status.

        Returns ``{"data": {"id": "<campaign_id>"}}`` (HTTP 201).
        The template and audience must exist before creating a campaign.
        """
        body: dict = {
            "name": options.name,
            "templateId": options.template_id,
            "audienceId": options.audience_id,
            "fromName": options.from_name,
            "fromEmail": options.from_email,
            "subjectA": options.subject_a,
        }
        if options.subject_b is not None:
            body["subjectB"] = options.subject_b
        return self._http._request("POST", "/v1/campaigns", body=body)

    def list(
        self,
        *,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> dict:
        """List campaigns.

        Returns a paginated response.

        Args:
            status: Filter by status (``draft``, ``sending``, ``scheduled``,
                ``paused``, ``completed``).
        """
        return self._http._request(
            "GET",
            "/v1/campaigns",
            params={"status": status, "limit": limit, "after": after},
        )

    def get(self, campaign_id: str) -> dict:
        """Get full campaign details including stats."""
        return self._http._request("GET", f"/v1/campaigns/{campaign_id}")

    def get_stats(self, campaign_id: str) -> dict:
        """Get delivery statistics and computed rates for a campaign.

        Returns::

            {
                "data": {
                    "campaignId": str,
                    "status": str,
                    "stats": {
                        "total": int, "sent": int, "delivered": int,
                        "opened": int, "clicked": int, "bounced": int,
                    },
                    "rates": {
                        "deliveryRate": float,
                        "openRate": float,
                        "clickRate": float,
                        "bounceRate": float,
                    },
                }
            }
        """
        return self._http._request("GET", f"/v1/campaigns/{campaign_id}/stats")

    def send(self, campaign_id: str, *, scheduled_at: Optional[str] = None) -> dict:
        """Send or schedule a campaign.

        Only campaigns in *draft* or *paused* status can be sent.

        Args:
            campaign_id: The campaign to send.
            scheduled_at: ISO-8601 datetime for future delivery. Omit to send
                immediately.

        Returns ``{"data": {"status": "sending" | "scheduled"}}``.
        """
        body: dict = {}
        if scheduled_at is not None:
            body["scheduledAt"] = scheduled_at
        return self._http._request(
            "POST", f"/v1/campaigns/{campaign_id}/send", body=body
        )

    def pause(self, campaign_id: str) -> dict:
        """Pause a *sending* or *scheduled* campaign.

        Returns ``{"data": {"status": "paused"}}``.
        Resume by calling :meth:`send` again.
        """
        return self._http._request("POST", f"/v1/campaigns/{campaign_id}/pause")

    def test_send(self, campaign_id: str, to: str) -> dict:
        """Send a test email for a campaign to a specific address.

        The test is sent with ``[TEST]`` prepended to the subject. Does not
        count against campaign stats.

        Returns ``{"data": {"emailId": str}}``.
        """
        return self._http._request(
            "POST",
            f"/v1/campaigns/{campaign_id}/test-send",
            body={"to": to},
        )
