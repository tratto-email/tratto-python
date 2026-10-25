from .client import Tratto
from .types import (
    Attachment,
    AudienceRule,
    BatchEmailError,
    BatchEmailResult,
    CreateAudienceOptions,
    CreateCampaignOptions,
    CreateContactOptions,
    CreateTemplateOptions,
    CreateWebhookOptions,
    EmailAttachment,
    FailedEventData,
    SendBatchResult,
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
    "SendBatchResult",
    "BatchEmailResult",
    "BatchEmailError",
    "EmailAttachment",
    # Attachments
    "Attachment",
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
    "FailedEventData",
]

from ._http import _SDK_VERSION

__version__ = _SDK_VERSION
