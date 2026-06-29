from typing import Optional

from .._http import HttpClient
from ..types import AudienceRule, CreateAudienceOptions


class AudiencesResource:
    """Methods for the ``/v1/audiences`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(self, options: CreateAudienceOptions) -> dict:
        """Create a new audience.

        Returns ``{"data": {"id": "<audience_id>"}}`` (HTTP 201).
        """
        body: dict = {"name": options.name}
        if options.description is not None:
            body["description"] = options.description
        if options.rules is not None:
            body["rules"] = [
                {"field": r.field, "operator": r.operator, "value": r.value}
                for r in options.rules
            ]
        return self._http._request("POST", "/v1/audiences", body=body)

    def list(
        self,
        *,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> dict:
        """List all audiences.

        Returns a paginated response::

            {
                "data": [{"id": str, "name": str, "contactCount": int, ...}],
                "pagination": {"hasMore": bool, "nextCursor": str | None}
            }
        """
        return self._http._request(
            "GET",
            "/v1/audiences",
            params={"limit": limit, "after": after},
        )

    def get(self, audience_id: str) -> dict:
        """Get a single audience, including its segmentation rules."""
        return self._http._request("GET", f"/v1/audiences/{audience_id}")

    def add_contacts(self, audience_id: str, contact_ids: list[str]) -> dict:
        """Add contacts to an audience (up to 500 per call).

        Returns::

            {
                "data": {
                    "added": int,
                    "alreadyInAudience": int,
                    "notFound": int,
                }
            }
        """
        return self._http._request(
            "POST",
            f"/v1/audiences/{audience_id}/contacts",
            body={"contactIds": contact_ids},
        )
