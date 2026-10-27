from ._http import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, HttpClient
from .resources import (
    AnalyticsResource,
    AttachmentsResource,
    AudiencesResource,
    CampaignsResource,
    ContactsResource,
    DomainsResource,
    EmailsResource,
    FlowsResource,
    TemplatesResource,
    WebhooksResource,
    WorkspaceResource,
)


class Tratto:
    """Tratto API client.

    Instantiate with your API key and access each resource via attributes::

        from tratto import Tratto

        client = Tratto("tratto_live_…")

        # Send an email
        result = client.emails.send(...)

        # Manage contacts
        client.contacts.create(...)
        client.contacts.list(status="subscribed")

    Args:
        api_key: Your Tratto API key (``tratto_live_…``). Get one at
            https://app.tratto.email/settings/api-keys.
        base_url: Override the API base URL. Useful for testing against a
            local or staging environment.
        timeout: Seconds to wait for each request (connect and each read)
            before raising :class:`TrattoError` with ``code="timeout"`` and
            ``status_code=0``. Defaults to 30.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        http = HttpClient(api_key, base_url, timeout)

        self.emails: EmailsResource = EmailsResource(http)
        """Send and retrieve transactional emails."""

        self.contacts: ContactsResource = ContactsResource(http)
        """Create, update, and import contacts."""

        self.audiences: AudiencesResource = AudiencesResource(http)
        """Create and manage audience segments."""

        self.templates: TemplatesResource = TemplatesResource(http)
        """Manage reusable email templates with version history."""

        self.attachments: AttachmentsResource = AttachmentsResource(http)
        """Upload files to attach to emails."""

        self.domains: DomainsResource = DomainsResource(http)
        """Register and verify sender domains."""

        self.campaigns: CampaignsResource = CampaignsResource(http)
        """Create, send, and track marketing campaigns."""

        self.webhooks: WebhooksResource = WebhooksResource(http)
        """Register webhook endpoints and inspect delivery history."""

        self.flows: FlowsResource = FlowsResource(http)
        """Build automations that react to contact and email events."""

        self.analytics: AnalyticsResource = AnalyticsResource(http)
        """Delivery and engagement metrics, as totals or a daily series."""

        self.workspace: WorkspaceResource = WorkspaceResource(http)
        """Workspace settings and team membership."""
