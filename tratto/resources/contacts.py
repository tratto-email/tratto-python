from typing import Optional

from .._http import HttpClient
from ..types import CreateContactOptions, UpdateContactOptions


class ContactsResource:
    """Methods for the ``/v1/contacts`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(self, options: CreateContactOptions) -> dict:
        """Create a new contact.

        Returns ``{"data": {"id": "<contact_id>"}}`` (HTTP 201).
        Raises :class:`~tratto.TrattoError` with code ``CONFLICT`` if the
        email address already exists in your contact list.
        """
        body: dict = {
            "email": options.email,
            "status": options.status,
            "tags": options.tags,
            "customFields": options.custom_fields,
        }
        if options.first_name is not None:
            body["firstName"] = options.first_name
        if options.last_name is not None:
            body["lastName"] = options.last_name
        return self._http._request("POST", "/v1/contacts", body=body)

    def list(
        self,
        *,
        status: Optional[str] = None,
        audience_id: Optional[str] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> dict:
        """List contacts with optional filters.

        Returns a paginated response::

            {
                "data": [...],
                "pagination": {"hasMore": bool, "nextCursor": str | None}
            }

        Args:
            status: Filter by status (``subscribed``, ``unsubscribed``,
                ``bounced``, ``complained``).
            audience_id: Return only contacts in this audience.
            tag: Return only contacts with this tag.
            limit: Results per page (1–100, default 50).
            after: Cursor from the previous page's ``nextCursor``.
        """
        return self._http._request(
            "GET",
            "/v1/contacts",
            params={
                "status": status,
                "audienceId": audience_id,
                "tag": tag,
                "limit": limit,
                "after": after,
            },
        )

    def update(self, contact_id: str, options: UpdateContactOptions) -> dict:
        """Update a contact's fields. Only supplied fields are changed.

        Setting ``status`` to ``unsubscribed`` records an ``unsubscribedAt``
        timestamp on the contact.
        """
        body: dict = {}
        if options.first_name is not None:
            body["firstName"] = options.first_name
        if options.last_name is not None:
            body["lastName"] = options.last_name
        if options.status is not None:
            body["status"] = options.status
        if options.tags is not None:
            body["tags"] = options.tags
        if options.custom_fields is not None:
            body["customFields"] = options.custom_fields
        return self._http._request("PATCH", f"/v1/contacts/{contact_id}", body=body)

    def import_csv(self, csv_text: str) -> dict:
        """Import contacts from CSV text (async — returns a job ID to poll).

        The CSV must have at least an ``email`` column. Optional columns:
        ``firstName`` / ``first_name``, ``lastName`` / ``last_name``,
        ``status``, ``tags`` (semicolon-separated values).

        Maximum 50,000 rows per import.

        Returns ``{"data": {"jobId": str, "totalRows": int}}``.
        Poll :meth:`get_import_job` until ``status != "processing"``.

        Example::

            csv = "email,firstName\\nalice@example.com,Alice"
            job = client.contacts.import_csv(csv)
            job_id = job["data"]["jobId"]
        """
        return self._http._request_raw(
            "POST",
            "/v1/contacts/import",
            body=csv_text.encode(),
            content_type="text/csv",
        )

    def get_import_job(self, job_id: str) -> dict:
        """Poll the status of a CSV import job.

        Returns::

            {
                "data": {
                    "jobId": str,
                    "status": "processing" | "completed" | "failed",
                    "totalRows": int,
                    "processedRows": int,
                    "failedRows": int,
                    "errors": list[str],   # up to 20 sample errors
                    "completedAt": str | None,
                }
            }
        """
        return self._http._request("GET", f"/v1/contacts/import/{job_id}")
