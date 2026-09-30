# Contributing to tratto-python

Thank you for helping improve the official Tratto Python SDK! This guide covers
everything you need to get started contributing.

---

## Code of Conduct

Be respectful and constructive. We follow the
[Contributor Covenant v2.1](./CODE_OF_CONDUCT.md).

---

## Ways to contribute

- **Bug reports** — open an issue with steps to reproduce, expected behaviour, and actual behaviour.
- **Feature requests** — open an issue describing the use-case before writing code.
- **Pull requests** — see the workflow below.
- **Documentation** — typos, clarifications, and extra examples are always welcome.

---

## Development setup

**Requirements:** Python 3.10+, `pip`.

```bash
# 1. Fork the repository on GitHub, then clone your fork
git clone https://github.com/<your-username>/tratto-python.git
cd tratto-python

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install the package in editable mode with dev dependencies
pip install -e ".[dev]"
```

---

## Running the tests

```bash
pytest
```

With coverage report:

```bash
pytest --cov=tratto --cov-report=term-missing
```

Tests live in `tests/` and **must not make real network requests** — use
`unittest.mock.patch` to mock `urllib.request.urlopen`.

---

## Linting and type checking

```bash
# Style
ruff check tratto tests examples scripts

# Types
mypy tratto examples scripts
```

All checks must pass before a PR is merged. `examples/` and `scripts/` are in
the perimeter on purpose: the examples are the public API used the way a
customer uses it, so a renamed method or a changed option type breaks the lint
job instead of a customer's build.

Note that the resource methods return a bare `dict`, so the checks catch
mistakes in the **calls** (unknown method, wrong argument type) but not in the
**response** fields an example reads: `email["stauts"]` typechecks fine.

This is not theoretical. The first version of `examples/` passed ruff and mypy
while being broken at runtime in every file: the API wraps every payload in an
envelope (`{"data": …}`, with `"pagination"` beside it on list endpoints) and
the examples read fields straight off the return value. Running one found it in
a second; the static checks never would. `tests/test_examples_envelope.py` now
guards the envelope specifically — but not the field names inside it, which
only the staging smoke test below can check. See
[#27](https://github.com/tratto-email/tratto-python/issues/27).

Your local `ruff` can be older than CI's, which installs the latest release on
every run. Run `pip install -U ruff mypy` before trusting a green local check.

---

## Staging smoke test (manual, before a release)

Everything in `tests/` mocks the network, so nothing in CI notices if the API
renames a field. `scripts/staging_smoke.py` is the one thing that does: it runs
a real round-trip against `api-staging.tratto.email` — create a contact, create
and publish a template, send an email, read its status and events back — and
removes what it created.

It is **not** in CI, by design: the org has a hard 3000 min/month Actions
budget. It is a manual rite, run before publishing a release, like the
dashboard E2E suite.

```bash
cp .env.example .env     # .env is gitignored, the key never enters the repo
# fill in TRATTO_API_KEY and TRATTO_FROM_EMAIL
python scripts/staging_smoke.py
```

- **The key must be a test key** (`tratto_test_…`). The script refuses a live
  one: sends go to `delivered@simulator.tratto.email`, so no real inbox is
  touched and the account's bounce rate does not move.
- A missing variable stops the run **naming the variable**. There is no silent
  skip: a check that quietly does nothing is worse than no check.
- **No flows.** They are the only v1 resource without fine-grained scopes, so
  covering them would need a key with the `*` permission. They stay in
  `examples/flows.py`, out of the executable script.
- **One residue is expected**: the API has no delete route for contacts, so the
  smoke contact is left unsubscribed at a `@simulator.tratto.email` address.
  The script says so on the last line.
- Revoke the key when you are done.

---

## Pull request workflow

1. **Open an issue first** (except for trivial fixes like typos).
2. Fork and create a feature branch:
   ```bash
   git checkout -b feat/your-feature
   ```
3. Make your changes. Keep commits focused and descriptive.
4. Add or update tests for every changed behaviour.
5. Run `pytest`, `ruff check`, and `mypy` locally — fix any failures.
6. Push your branch and open a PR against `main`.

### PR checklist

- [ ] Tests added or updated
- [ ] `ruff check tratto tests examples scripts` passes
- [ ] `mypy tratto examples scripts` passes
- [ ] A new public method has an example in `examples/`
- [ ] Public API changes reflected in `README.md`

---

## Project structure

```
tratto-python/
├── tratto/
│   ├── __init__.py          # public exports
│   ├── _http.py             # internal HTTP client
│   ├── client.py            # Tratto main class
│   ├── types.py             # option dataclasses + TrattoError
│   └── resources/
│       ├── __init__.py
│       ├── emails.py
│       ├── contacts.py
│       ├── audiences.py
│       ├── templates.py
│       ├── domains.py
│       ├── campaigns.py
│       ├── webhooks.py
│       ├── flows.py
│       ├── analytics.py
│       └── workspace.py
├── examples/                # one runnable example per resource, linted+typechecked
├── scripts/
│   └── staging_smoke.py     # manual round-trip against api-staging
├── tests/
│   └── test_client.py
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## Coding conventions

- **No external runtime dependencies.** The SDK uses only Python's standard library.
- **Python 3.10+** — use native generics (`list[str]`, `dict[str, str]`, `str | None`).
- **Strict type hints** on all public functions and methods (enforced by `mypy`, config in `[tool.mypy]` of `pyproject.toml`).
- **Dataclasses for option objects** — one per write operation, matching the API body.
- **snake_case** in Python maps to **camelCase** in JSON request bodies and responses.
- **Resource sub-clients** — each API resource group has its own class in `tratto/resources/`.
- Follow `ruff` defaults for code style (line length 100).
- Do not add `print` statements or logging to the SDK.

---

## Versioning

This SDK follows [Semantic Versioning](https://semver.org/):

| Bump | When |
|---|---|
| **Patch** (`0.x.y`) | Bug fixes, non-breaking improvements |
| **Minor** (`0.x.0`) | New API coverage, new optional fields |
| **Major** (`x.0.0`) | Breaking changes to the public API |

The version lives in one place: `version` in `pyproject.toml`. `tratto.__version__`
and the `User-Agent` header read it at import time via `importlib.metadata`, so after
a bump re-run `pip install -e ".[dev]"` for your local install to report the new value.

---

## Release process (maintainers only)

0. Run the [staging smoke test](#staging-smoke-test-manual-before-a-release).
1. Bump `version` in `pyproject.toml`.
2. Commit and merge to `main`.
3. Push a tag:
   ```bash
   git tag v0.x.y && git push --tags
   ```
4. GitHub Actions publishes to PyPI automatically via the `publish` workflow.

---

## License

By contributing you agree that your work will be licensed under the
[MIT License](./LICENSE).
