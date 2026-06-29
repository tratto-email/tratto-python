import json
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

from .types import TrattoError

DEFAULT_BASE_URL = "https://api.tratto.email"
_SDK_VERSION = "0.2.0"


class HttpClient:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[dict] = None,
        params: Optional[dict] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> dict:
        url = f"{self._base_url}{path}"
        if params:
            filtered = {k: str(v) for k, v in params.items() if v is not None}
            if filtered:
                url = f"{url}?{urlencode(filtered)}"

        data = json.dumps(body).encode() if body is not None else None
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"tratto-python/{_SDK_VERSION}",
        }
        if extra_headers:
            headers.update(extra_headers)

        req = Request(url, data=data, method=method, headers=headers)
        try:
            with urlopen(req) as res:
                raw = res.read()
                return json.loads(raw) if raw else {}
        except HTTPError as e:
            try:
                payload = json.loads(e.read())
                err = payload.get("error", {})
            except Exception:
                err = {}
            raise TrattoError(
                err.get("message", str(e)),
                err.get("code", "unknown_error"),
                e.code,
            ) from e

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        body: bytes,
        content_type: str,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> dict:
        url = f"{self._base_url}{path}"
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": content_type,
            "Accept": "application/json",
            "User-Agent": f"tratto-python/{_SDK_VERSION}",
        }
        if extra_headers:
            headers.update(extra_headers)

        req = Request(url, data=body, method=method, headers=headers)
        try:
            with urlopen(req) as res:
                raw = res.read()
                return json.loads(raw) if raw else {}
        except HTTPError as e:
            try:
                payload = json.loads(e.read())
                err = payload.get("error", {})
            except Exception:
                err = {}
            raise TrattoError(
                err.get("message", str(e)),
                err.get("code", "unknown_error"),
                e.code,
            ) from e
