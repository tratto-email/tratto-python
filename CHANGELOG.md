# Changelog

Releases before 2.0.0 are described in the
[GitHub releases](https://github.com/tratto-email/tratto-python/releases).

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
