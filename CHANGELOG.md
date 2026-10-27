# Changelog

Releases before 2.0.0 are described in the
[GitHub releases](https://github.com/tratto-email/tratto-python/releases).

## Unreleased

### Added

- `timeout` option on `Tratto(...)`, in seconds, default 30. A request that
  exceeds it raises `TrattoError` with `code="timeout"` and `status_code=0`.
  Before, a hung connection blocked the caller indefinitely (#37).

### Fixed

- Ids in URL paths are percent-encoded as a single segment, so an id that
  contains `/`, `?` or `#` can no longer change the route called (#46).

## 2.2.0

### Added

- `attachments.upload(content, *, filename, content_type)`,
  `attachments.get(id)` and `attachments.delete(id)` (`/v1/attachments`).
  `content` is `bytes` or a binary file object, sent as raw bytes and never
  JSON-encoded, also for `application/json`. Non-ASCII filenames are sent as
  `filename*=UTF-8''…` (RFC 6266 / RFC 5987). New types: `Attachment`,
  `EmailAttachment` (#55).
- `SendEmailOptions.attachments` (`[{"id": ...}]`), accepted by
  `emails.send` and `emails.send_batch`. `emails.get` returns `attachments`
  and, on failed emails, `failureReason` (an open set, e.g.
  `attachment_unavailable`) (#55).
- `WebhookEventType` includes `"failed"`; its `data` is typed as
  `FailedEventData` (`{reason, error}`) (#55).

## 2.1.0

### Added

- `emails.send_batch(emails, *, idempotency_key=None)` sends up to 100
  emails in one request (`POST /v1/emails/batch`). Each item is a
  `SendEmailOptions`; the idempotency key covers the whole batch, so an item
  carrying its own `idempotency_key` raises `ValueError` before any request.
  `scheduled_at` is not supported in a batch: the API answers 422. The
  response is typed as `SendBatchResult`: a 202 with failed items is returned,
  not raised, and each failed item carries an `error` and no `id` (#52).
- `TrattoError.details`: the per-field problems of a 422 `VALIDATION_ERROR`
  as sent by the API (e.g. `details[0]["path"] == "/emails/0/scheduledAt"`),
  `None` when absent (#52).

## 2.0.0

### Breaking

- All option classes must be built with keyword arguments:
  `SendEmailOptions`, `CreateContactOptions`, `UpdateContactOptions`,
  `AudienceRule`, `CreateAudienceOptions`, `CreateTemplateOptions`,
  `UpdateTemplateOptions`, `CreateCampaignOptions` and `CreateWebhookOptions`.
  Positional construction, such as `SendEmailOptions("a@b.c", "d@e.f", "Hi")`
  or `AudienceRule("plan", "equals", "pro")`, is no longer supported and
  raises `TypeError`. Code that already passes fields by name keeps working
  unchanged. A required field can then become optional in a later release
  without another breaking change (#19).

### Added

- `from_` on `SendEmailOptions` is optional. When omitted, the request carries
  no `from` and the API picks the workspace's transactional sender, then the
  workspace-wide default sender, and answers 422 `VALIDATION_ERROR` when
  neither is set (#19).

### Fixed

- The `workspace.update()` docstring now describes when `senders.transactional`
  applies: to `emails.send` calls without `from_` (#50).
