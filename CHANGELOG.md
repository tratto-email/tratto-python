# Changelog

Releases before 2.0.0 are described in the
[GitHub releases](https://github.com/tratto-email/tratto-python/releases).

## 2.0.0

### Breaking

- `SendEmailOptions` must be built with keyword arguments. Positional
  construction, such as `SendEmailOptions("a@b.c", "d@e.f", "Hi")`, is no
  longer supported and raises `TypeError`. Code that already passes
  `from_=`, `to=`, `subject=` by name keeps working unchanged (#19).

### Added

- `from_` on `SendEmailOptions` is optional. When omitted, the request carries
  no `from` and the API picks the workspace's transactional sender, then the
  workspace-wide default sender, and answers 422 `VALIDATION_ERROR` when
  neither is set (#19).

### Fixed

- The `workspace.update()` docstring now describes when `senders.transactional`
  applies: to `emails.send` calls without `from_` (#50).
