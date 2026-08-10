
from .._http import HttpClient


class WorkspaceResource:
    """Methods for the ``/v1/workspace`` endpoints.

    Workspace settings and team membership. Note that API keys are *not* here:
    they are issued from the dashboard, deliberately outside the SDKs.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get(self) -> dict:
        """Get the current workspace: name, slug, plan and default sender."""
        return self._http._request("GET", "/v1/workspace")

    def update(self, options: dict) -> dict:
        """Update workspace settings.

        Setting ``defaultFromEmail`` requires the address to be on a domain
        already verified for this workspace; otherwise the API answers 403.
        """
        return self._http._request("PATCH", "/v1/workspace", body=options)

    def delete(self) -> None:
        """Permanently delete the workspace and everything in it."""
        self._http._request("DELETE", "/v1/workspace")

    def update_preferences(self, options: dict) -> dict:
        """Update workspace preferences, such as language and timezone."""
        return self._http._request(
            "PATCH", "/v1/workspace/preferences", body=options
        )

    def invite_member(self, email: str, role: str) -> dict:
        """Invite someone to the workspace by email.

        Args:
            role: ``admin`` or ``member``.
        """
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
        """Remove a member from the workspace.

        The owner cannot be removed; the API answers 409.
        """
        self._http._request("DELETE", f"/v1/workspace/members/{user_id}")
