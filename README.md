# tratto-email

Python SDK for [Tratto](https://tratto.email) — send transactional and marketing email.

No external dependencies. Requires Python 3.10+.

## Installation

```bash
pip install tratto-email
```

## Usage

```python
from tratto import Tratto, SendEmailOptions

client = Tratto("tratto_live_...")

result = client.send_email(SendEmailOptions(
    from_="you@yourdomain.com",
    to="user@example.com",
    subject="Hello from Tratto",
    html="<p>This is a test email.</p>",
))

print(result["id"])
```

## API

### `Tratto(api_key, base_url?)`

### `client.send_email(options: SendEmailOptions) -> dict`

### `client.list_emails(*, status?, limit?, after?) -> dict`

### `client.get_email(email_id: str) -> dict`

## Documentation

Full docs at [tratto.email/docs](https://tratto.email/docs).

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT
