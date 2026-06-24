import json
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from .types import SendEmailOptions, TrattoError

DEFAULT_BASE_URL = "https://api.tratto.email"


class Tratto:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL):
        if not api_key:
            raise ValueError("api_key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        url = f"{self._base_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "tratto-email/0.1.0",
            },
        )
        try:
            with urlopen(req) as res:
                return json.loads(res.read())
        except HTTPError as e:
            payload = json.loads(e.read())
            err = payload.get("error", {})
            raise TrattoError(
                err.get("message", str(e)),
                err.get("code", "unknown_error"),
                e.code,
            ) from e

    def send_email(self, options: SendEmailOptions) -> dict:
        body = {
            "from": options.from_,
            "to": options.to,
            "subject": options.subject,
        }
        if options.html is not None:
            body["html"] = options.html
        if options.text is not None:
            body["text"] = options.text
        if options.reply_to is not None:
            body["replyTo"] = options.reply_to
        if options.cc is not None:
            body["cc"] = options.cc
        if options.bcc is not None:
            body["bcc"] = options.bcc
        if options.headers is not None:
            body["headers"] = options.headers
        if options.tags is not None:
            body["tags"] = options.tags

        result = self._request("POST", "/v1/emails", body)
        return result.get("data", result)

    def list_emails(
        self,
        *,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> dict:
        params: list[str] = []
        if status:
            params.append(f"status={status}")
        if limit:
            params.append(f"limit={limit}")
        if after:
            params.append(f"after={after}")
        qs = "?" + "&".join(params) if params else ""
        return self._request("GET", f"/v1/emails{qs}")

    def get_email(self, email_id: str) -> dict:
        return self._request("GET", f"/v1/emails/{email_id}")
