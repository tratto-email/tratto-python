from .client import Tratto
from .types import (
    AudienceRule,
    CreateAudienceOptions,
    CreateCampaignOptions,
    CreateContactOptions,
    CreateTemplateOptions,
    CreateWebhookOptions,
    SendEmailOptions,
    TrattoError,
    UpdateContactOptions,
    UpdateTemplateOptions,
)

__all__ = [
    "Tratto",
    "TrattoError",
    # Emails
    "SendEmailOptions",
    # Contacts
    "CreateContactOptions",
    "UpdateContactOptions",
    # Audiences
    "AudienceRule",
    "CreateAudienceOptions",
    # Templates
    "CreateTemplateOptions",
    "UpdateTemplateOptions",
    # Campaigns
    "CreateCampaignOptions",
    # Webhooks
    "CreateWebhookOptions",
]

from ._http import _SDK_VERSION

__version__ = _SDK_VERSION
