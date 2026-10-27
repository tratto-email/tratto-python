
import warnings

from .._http import HttpClient, _seg


class FlowsResource:
    """Methods for the ``/v1/flows`` endpoints.

    A flow is an automation: a trigger (a tag added to a contact, a contact
    joining an audience, an email event) followed by an ordered list of steps
    — ``send_email``, ``wait``, ``branch``, ``update_contact``,
    ``webhook_call``.

    A flow only runs while it is *active*: :meth:`create` and :meth:`update`
    leave it in ``draft``, and nothing is enrolled until :meth:`activate` is
    called.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        *,
        limit: int | None = None,
        after: str | None = None,
        status: str | None = None,
    ) -> dict:
        """List flows, newest first, paginated with ``limit`` and ``after``.

        Each flow's ``status`` is ``draft``, ``active`` or ``inactive``.

        Args:
            status: Deprecated and ignored by the API, which returns flows of
                every status. Filter on ``status`` in the response instead.
                Passing it emits a ``DeprecationWarning``; it will be removed
                in the next major version.
        """
        if status is not None:
            warnings.warn(
                "flows.list(status=...) is deprecated: the API ignores it and "
                "returns flows of every status. Filter on each flow's 'status' "
                "('draft', 'active' or 'inactive') in the response instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return self._http._request(
            "GET",
            "/v1/flows",
            params={"limit": limit, "after": after, "status": status},
        )

    def create(self, options: dict) -> dict:
        """Create a flow, in ``draft``.

        The flow does not enroll anyone until :meth:`activate` is called.
        """
        return self._http._request("POST", "/v1/flows", body=options)

    def get(self, flow_id: str) -> dict:
        """Get a single flow with its trigger and steps."""
        return self._http._request("GET", f"/v1/flows/{_seg(flow_id)}")

    def update(self, flow_id: str, options: dict) -> dict:
        """Update a flow's name, trigger or steps.

        Editing an active flow does not retroactively change contacts already
        enrolled: they finish on the step list they started with.
        """
        return self._http._request("PATCH", f"/v1/flows/{_seg(flow_id)}", body=options)

    def delete(self, flow_id: str) -> None:
        """Permanently delete a flow."""
        self._http._request("DELETE", f"/v1/flows/{_seg(flow_id)}")

    def activate(self, flow_id: str) -> dict:
        """Activate a flow so its trigger starts enrolling contacts."""
        return self._http._request("POST", f"/v1/flows/{_seg(flow_id)}/activate")

    def deactivate(self, flow_id: str) -> dict:
        """Pause a flow.

        The trigger stops enrolling new contacts. Contacts already mid-flow
        stay where they are.
        """
        return self._http._request("POST", f"/v1/flows/{_seg(flow_id)}/deactivate")
