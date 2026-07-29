from dataclasses import dataclass, field
from typing import Literal

# ── Errors ────────────────────────────────────────────────────────────────────

class TrattoError(Exception):
    """Raised when the Tratto API returns an error response.

    Attributes:
        code: Machine-readable error code (e.g. ``"NOT_FOUND"``).
        status_code: HTTP status code (e.g. ``404``).
    """

    def __init__(self, message: str, code: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


# ── Email types ───────────────────────────────────────────────────────────────

@dataclass
class SendEmailOptions:
    """Options for sending a transactional email.

    At least one of *html*, *text*, or *template_id* is required.
    """

    from_: str
    """Sender address. Must use a verified domain.

    Accepts either ``'user@domain.com'`` or ``'Display Name <user@domain.com>'``.
    """

    to: str | list[str]
    """Recipient address(es)."""

    subject: str
    """Email subject line (max 998 characters)."""

    html: str | None = None
    """HTML body."""

    text: str | None = None
    """Plain-text body."""

    reply_to: str | None = None
    """Reply-to address."""

    cc: str | list[str] | None = None
    bcc: str | list[str] | None = None
    headers: dict[str, str] | None = None
    """Custom email headers."""

    tags: list[str] | None = None
    """Free-form tags for filtering and analytics."""

    template_id: str | None = None
    """ID of a saved template to render."""

    variables: dict[str, object] | None = None
    """Template variables (used with *template_id*)."""

    scheduled_at: str | None = None
    """ISO-8601 datetime to delay delivery. Omit to send immediately."""

    idempotency_key: str | None = None
    """UUID for idempotent sends. Duplicate requests with the same key return
    the original response without sending a second email."""


# ── Contact types ─────────────────────────────────────────────────────────────

ContactStatus = Literal["subscribed", "unsubscribed", "bounced", "complained"]


@dataclass
class CreateContactOptions:
    """Options for creating a contact."""

    email: str
    first_name: str | None = None
    last_name: str | None = None
    status: str = "subscribed"
    tags: list[str] = field(default_factory=list)
    custom_fields: dict[str, object] = field(default_factory=dict)


@dataclass
class UpdateContactOptions:
    """Options for updating a contact. Only supplied fields are changed."""

    first_name: str | None = None
    last_name: str | None = None
    status: str | None = None
    """One of ``subscribed``, ``unsubscribed``, ``bounced``, ``complained``."""
    tags: list[str] | None = None
    custom_fields: dict[str, object] | None = None


# ── Audience types ────────────────────────────────────────────────────────────

AudienceOperator = Literal[
    "equals", "not_equals", "contains", "not_contains", "array_contains"
]


@dataclass
class AudienceRule:
    """A single segmentation rule for an audience."""

    field: str
    """Contact field to evaluate (e.g. ``'plan'``, ``'tags'``)."""

    operator: str
    """Comparison operator. One of: ``equals``, ``not_equals``, ``contains``,
    ``not_contains``, ``array_contains``."""

    value: str | int | bool
    """Value to compare against."""


@dataclass
class CreateAudienceOptions:
    """Options for creating an audience."""

    name: str
    description: str | None = None
    rules: list[AudienceRule] | None = None
    """Optional segmentation rules. Contacts matching all rules are auto-added."""


# ── Template types ────────────────────────────────────────────────────────────

TemplateStatus = Literal["draft", "published"]


@dataclass
class CreateTemplateOptions:
    """Options for creating an email template."""

    name: str
    """Display name for this template (max 256 characters)."""

    html: str = ""
    """Initial HTML content. Use ``{{variable_name}}`` for template variables."""


@dataclass
class UpdateTemplateOptions:
    """Options for updating a template. Only supplied fields are changed.

    Changing *html* automatically creates a new version.
    """

    name: str | None = None
    html: str | None = None
    status: str | None = None
    """Set to ``'published'`` to make the template available for campaigns."""


# ── Campaign types ────────────────────────────────────────────────────────────

CampaignStatus = Literal["draft", "sending", "scheduled", "paused", "completed"]


@dataclass
class CreateCampaignOptions:
    """Options for creating a marketing campaign."""

    name: str
    """Internal campaign name (max 200 characters)."""

    template_id: str
    """ID of the template to send. Must be in ``published`` status."""

    audience_id: str
    """ID of the audience to send to."""

    from_name: str
    """Sender display name (e.g. ``'Acme Newsletter'``)."""

    from_email: str
    """Sender email address. Must use a verified domain."""

    subject_a: str
    """Primary subject line (max 998 characters)."""

    subject_b: str | None = None
    """Alternate subject line for A/B testing (max 998 characters)."""


# ── Webhook types ─────────────────────────────────────────────────────────────

WebhookEventType = Literal[
    "sent", "delivered", "opened", "clicked", "bounced", "complained", "unsubscribed"
]


@dataclass
class CreateWebhookOptions:
    """Options for registering a webhook endpoint."""

    url: str
    """HTTPS URL that Tratto will POST events to."""

    events: list[str]
    """Event types to subscribe to. At least one required.

    Valid values: ``sent``, ``delivered``, ``opened``, ``clicked``,
    ``bounced``, ``complained``, ``unsubscribed``.
    """
