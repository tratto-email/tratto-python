
import warnings

from .._http import HttpClient


class WorkspaceResource:
    """Methods for the ``/v1/workspace`` endpoints.

    Workspace settings and team membership. Note that API keys are *not* here:
    they are issued from the dashboard, deliberately outside the SDKs.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get(self) -> dict:
        """Get the current workspace: name, slug, plan and senders.

        Besides the workspace-wide ``defaultFromName``/``defaultFromEmail``, an
        API from 0.5.7 on returns ``senders``: one entry per send type —
        ``marketing``, ``automation``, ``transactional`` — each either ``None``
        or ``{"fromEmail": ..., "fromName": ..., "replyTo": ...}``.

        A type set to ``None`` is **not configured and inherits** the
        workspace-wide default; it is never a reason for a send to be refused.
        Read it defensively: an older API does not return the key at all.

            senders = workspace.get().get("senders") or {}
            marketing = senders.get("marketing")  # may be None
        """
        return self._http._request("GET", "/v1/workspace")

    def update(self, options: dict) -> dict:
        """Update workspace settings.

        Setting ``defaultFromEmail`` requires the address to be on a domain
        already verified for this workspace; otherwise the API answers 403. The
        same applies to every address in ``senders``.

        Writing ``senders`` is **partial**: sending one type leaves the other
        two untouched, and ``None`` on a type puts it back to inheriting the
        workspace-wide default.

            # only marketing; automation and transactional stay as they are
            client.workspace.update(
                {"senders": {"marketing": {"fromEmail": "news@acme.test", "fromName": "Acme"}}}
            )

            # back to the workspace-wide default for that type
            client.workspace.update({"senders": {"marketing": None}})

        ``fromEmail`` and ``fromName`` travel together: an entry carrying only
        one of the two is refused.

        Which type applies where: ``marketing`` for campaigns and template test
        sends, ``automation`` for the emails a flow sends (resolved when the
        flow is activated), ``transactional`` for API sends that carry no
        ``from`` of their own.
        """
        return self._http._request("PATCH", "/v1/workspace", body=options)

    def delete(self) -> None:
        """Deprecated: this call cannot succeed.

        The API refuses ``DELETE /v1/workspace`` for every API key (403): a
        workspace is deleted from the dashboard, by its owner. This method
        will be removed in the next major version.
        """
        warnings.warn(
            "workspace.delete() is deprecated: the API refuses it for every "
            "API key. Delete the workspace from the dashboard.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._http._request("DELETE", "/v1/workspace")

    def update_preferences(self, options: dict) -> dict:
        """Update workspace preferences, such as language and timezone."""
        return self._http._request(
            "PATCH", "/v1/workspace/preferences", body=options
        )

    def invite_member(self, email: str, role: str) -> dict:
        """Deprecated: this call cannot succeed.

        The API refuses ``POST /v1/workspace/members/invite`` for every API
        key (403): members are invited from the dashboard, by the workspace
        owner. This method will be removed in the next major version.
        """
        warnings.warn(
            "workspace.invite_member() is deprecated: the API refuses it for "
            "every API key. Invite members from the dashboard.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._http._request(
            "POST",
            "/v1/workspace/members/invite",
            body={"email": email, "role": role},
        )

    def update_member(self, user_id: str, role: str) -> dict:
        """Change a member's role."""
        return self._http._request(
            "PATCH", f"/v1/workspace/members/{user_id}", body={"role": role}
        )

    def remove_member(self, user_id: str) -> None:
        """Deprecated: this call cannot succeed.

        The API refuses ``DELETE /v1/workspace/members/:userId`` for every
        API key (403): members are removed from the dashboard, by the
        workspace owner. This method will be removed in the next major version.
        """
        warnings.warn(
            "workspace.remove_member() is deprecated: the API refuses it for "
            "every API key. Remove members from the dashboard.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._http._request("DELETE", f"/v1/workspace/members/{user_id}")
