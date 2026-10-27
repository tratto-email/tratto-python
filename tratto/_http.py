import json
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .types import TrattoError

DEFAULT_BASE_URL = "https://api.tratto.email"
DEFAULT_TIMEOUT = 60.0
try:
    _SDK_VERSION = _pkg_version("tratto-email")
except PackageNotFoundError:  # source checkout never pip-installed
    _SDK_VERSION = "0.0.0+unknown"


def _seg(value: object) -> str:
    """Encode one variable path segment, so an id with ``/``, ``?`` or ``#``
    cannot change the route that is called."""
    return quote(str(value), safe="")


def _tratto_error(e: HTTPError) -> TrattoError:
    """Turn an HTTP error response into a :class:`TrattoError`.

    Both request paths go through here, so a field read once is read by the
    whole SDK. ``suggestion``, ``docs`` and ``details`` are optional in the API payload:
    absent means ``None``, never an empty string.
    """
    try:
        err = json.loads(e.read()).get("error", {})
    except Exception:  # noqa: BLE001 — error body may not be valid JSON at all
        err = {}
    return TrattoError(
        err.get("message", str(e)),
        err.get("code", "unknown_error"),
        e.code,
        suggestion=err.get("suggestion"),
        docs=err.get("docs"),
        details=err.get("details"),
    )


class HttpClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if timeout <= 0:
            raise ValueError("timeout must be a positive number of seconds")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _send(self, req: Request) -> dict:
        try:
            with urlopen(req, timeout=self._timeout) as res:
                raw = res.read()
                return json.loads(raw) if raw else {}
        except HTTPError as e:
            raise _tratto_error(e) from e
        except (TimeoutError, URLError) as e:
            # urlopen raises TimeoutError on a slow read and URLError wrapping
            # it on a slow connect. Other network errors propagate unchanged.
            if isinstance(e, URLError) and not isinstance(e.reason, TimeoutError):
                raise
            raise TrattoError(
                f"Request timed out after {self._timeout} seconds",
                "timeout",
                0,
            ) from e

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        params: dict | None = None,
        extra_headers: dict[str, str] | None = None,
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
        return self._send(req)

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        body: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
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
        return self._send(req)
