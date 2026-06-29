from typing import Optional

from .._http import HttpClient
from ..types import CreateTemplateOptions, UpdateTemplateOptions


class TemplatesResource:
    """Methods for the ``/v1/templates`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        *,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """List templates.

        Returns a paginated response with ``id``, ``name``, ``status``,
        ``version``, ``createdAt``, and ``updatedAt`` for each template.

        Args:
            status: Filter by ``draft`` or ``published``.
        """
        return self._http._request(
            "GET",
            "/v1/templates",
            params={"limit": limit, "after": after, "status": status},
        )

    def create(self, options: CreateTemplateOptions) -> dict:
        """Create a new template in *draft* status.

        Returns the full template object including ``id``, ``name``, ``html``,
        ``status``, ``version``, ``createdAt``, and ``updatedAt``.
        """
        return self._http._request(
            "POST",
            "/v1/templates",
            body={"name": options.name, "html": options.html},
        )

    def get(self, template_id: str) -> dict:
        """Get a single template with its current HTML."""
        return self._http._request("GET", f"/v1/templates/{template_id}")

    def update(self, template_id: str, options: UpdateTemplateOptions) -> dict:
        """Update a template.

        Changing *html* automatically creates a new version, incrementing the
        ``version`` counter. Retrieve old versions with :meth:`get_version`.
        """
        body: dict = {}
        if options.name is not None:
            body["name"] = options.name
        if options.html is not None:
            body["html"] = options.html
        if options.status is not None:
            body["status"] = options.status
        return self._http._request("PATCH", f"/v1/templates/{template_id}", body=body)

    def delete(self, template_id: str) -> None:
        """Permanently delete a template.

        This is irreversible. Campaigns referencing this template will fail if
        they haven't been sent yet.
        """
        self._http._request("DELETE", f"/v1/templates/{template_id}")

    def list_versions(self, template_id: str) -> dict:
        """List all saved versions of a template (most recent first, max 20).

        Returns::

            {"data": [{"version": int, "savedAt": str}, ...]}
        """
        return self._http._request("GET", f"/v1/templates/{template_id}/versions")

    def get_version(self, template_id: str, version: int) -> dict:
        """Get the HTML for a specific template version.

        Returns::

            {"data": {"version": int, "html": str, "savedAt": str}}
        """
        return self._http._request(
            "GET", f"/v1/templates/{template_id}/versions/{version}"
        )

    def test_send(
        self,
        template_id: str,
        to: str,
        variables: Optional[dict[str, str]] = None,
    ) -> dict:
        """Send a test email using this template to a specific address.

        Useful for previewing a template with real variable values before
        publishing it or building a campaign.
        """
        return self._http._request(
            "POST",
            f"/v1/templates/{template_id}/test-send",
            body={"to": to, "variables": variables or {}},
        )
