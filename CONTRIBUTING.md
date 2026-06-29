# Contributing to tratto-python

Thank you for helping improve the official Tratto Python SDK! This guide covers
everything you need to get started contributing.

---

## Code of Conduct

Be respectful and constructive. We follow the
[Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

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
ruff check tratto tests

# Types
mypy tratto
```

All checks must pass before a PR is merged.

---

## Pull request workflow

1. **Open an issue first** (except for trivial fixes like typos).
2. Fork and create a feature branch:
   ```bash
   git checkout -b feat/your-feature
   ```
3. Make your changes. Keep commits focused and descriptive.
4. Add or update tests for every changed behaviour.
5. Run `pytest`, `ruff check`, and `mypy tratto` locally — fix any failures.
6. Push your branch and open a PR against `main`.

### PR checklist

- [ ] Tests added or updated
- [ ] `ruff check tratto tests` passes
- [ ] `mypy tratto` passes
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
│       └── webhooks.py
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
- **Strict type hints** on all public functions and methods (enforced by `mypy --strict`).
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

When cutting a release, update:
- `__version__` in `tratto/__init__.py`
- `_SDK_VERSION` in `tratto/_http.py`
- `version` in `pyproject.toml`

---

## Release process (maintainers only)

1. Bump the version in the three files above.
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
