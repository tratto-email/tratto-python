import hashlib
import hmac
import re
import time

_TIMESTAMP = re.compile(r"[0-9]{1,15}")


def verify_webhook(
    payload: bytes | str,
    header: str | None,
    secret: str,
    *,
    tolerance_seconds: int = 300,
    now_ms: int | None = None,
) -> bool:
    """Verify the ``X-Tratto-Signature`` header of a webhook delivery.

    The header is ``t=<unix ms>,v1=<hex>``; ``v1`` may repeat during a secret
    rotation and any match is accepted. The signature is HMAC-SHA256 of
    ``"{t}.{raw body}"`` keyed with the whole secret, ``whsec_`` prefix
    included, the same as the Tratto webhook signer.

    Args:
        payload: The raw request body, exactly as received (e.g. Flask's
            ``request.get_data()``). Never a re-serialized JSON object: a
            change in whitespace or key order breaks the signature.
        header: The ``X-Tratto-Signature`` header, ``None`` when missing.
        secret: The webhook secret, ``whsec_...``.
        tolerance_seconds: Maximum distance between ``t`` and now, in the
            past or in the future. Default 300 (5 minutes).
        now_ms: Current time in milliseconds, for tests. Default: the clock.

    Returns:
        ``True`` only for an authentic, fresh delivery. A missing, malformed,
        stale or non-matching header returns ``False``, never raises.

    Raises:
        ValueError: On an empty *secret* or a negative *tolerance_seconds*
            (configuration errors, not bad requests).

    Example::

        if not verify_webhook(request.get_data(),
                              request.headers.get("X-Tratto-Signature"),
                              os.environ["TRATTO_WEBHOOK_SECRET"]):
            abort(401)
    """
    if not secret:
        raise ValueError("secret is required")
    if tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must not be negative")

    timestamp: str | None = None
    signatures: list[bytes] = []
    for part in (header or "").split(","):
        pair = part.split("=")  # hex and digits never contain "=": such a part is invalid
        if len(pair) != 2:
            continue
        name, value = pair[0].strip(), pair[1].strip()
        if name == "t":
            if timestamp is not None:
                return False  # two timestamps: ambiguous, never guess
            timestamp = value
        elif name == "v1" and value:
            signatures.append(value.lower().encode())

    # Digits only: int() would also accept "+123", " 123" or "1_000".
    if timestamp is None or not signatures or not _TIMESTAMP.fullmatch(timestamp):
        return False

    now = now_ms if now_ms is not None else time.time_ns() // 1_000_000
    if abs(now - int(timestamp)) > tolerance_seconds * 1000:
        return False

    body = payload.encode() if isinstance(payload, str) else payload
    # Signed over the timestamp string exactly as received, never a re-formatted number.
    expected = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256)
    digest = expected.hexdigest().encode()
    return any(hmac.compare_digest(digest, s) for s in signatures)
