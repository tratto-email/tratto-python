from .client import Tratto
from .types import (
    AudienceRule,
    CreateAudienceOptions,
    CreateCampaignOptions,
    CreateContactOptions,
    CreateTemplateOptions,
    CreateWebhookOptions,
    TrattoError,
    SendEmailOptions,
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

__version__ = "0.2.0"
