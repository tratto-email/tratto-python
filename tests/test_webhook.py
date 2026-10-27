import hashlib
import hmac
import time

import pytest

from tratto import verify_webhook

# Fixed vector, produced by running tratto-api's own signer
# (functions/webhookFanout/src/index.ts signPayload, origin/main) on these inputs.
# The same vector is used by the PHP SDK (tratto-php tests/WebhookTest.php).
SECRET = "whsec_abababababababababababababababababababababababab"
T = "1784977714054"
BODY = '{"id":"evt_1","type":"delivered"}'
V1 = "05e8e3cddebbeca892e5fd50622431ca3059594f22001ef9f7a2c0566a44fcc8"
NOW = 1784977714054


def sign(t: str, body: str = BODY) -> str:
    return hmac.new(SECRET.encode(), f"{t}.{body}".encode(), hashlib.sha256).hexdigest()


def verify(header, body=BODY, secret=SECRET, tolerance=300, now_ms=NOW):
    return verify_webhook(body, header, secret, tolerance_seconds=tolerance, now_ms=now_ms)


def test_accepts_the_fixed_vector():
    assert sign(T) == V1, "the vector itself"
    assert verify(f"t={T},v1={V1}")


def test_accepts_bytes_and_str_payloads():
    assert verify(f"t={T},v1={V1}", body=BODY.encode())
    assert verify(f"t={T},v1={V1}", body=BODY)


def test_accepts_whitespace_uppercase_hex_and_unknown_fields():
    assert verify(f" t = {T} , v1 = {V1.upper()} ,v2=future,junk")
    assert verify(f"junk,t={T},,x=1=2,v1={V1}"), "a malformed part is skipped"


def test_accepts_any_of_several_v1():
    other = "0" * 64
    assert verify(f"t={T},v1={other},v1={V1}")
    assert verify(f"t={T},v1={V1},v1={other}")
    assert verify(f"v1={V1},t={T}"), "order of fields does not matter"


@pytest.mark.parametrize("field", ["v0", "v2", "V1", "sig", "t1"])
def test_accepts_the_signature_only_under_v1(field):
    assert not verify(f"t={T},{field}={V1}")


@pytest.mark.parametrize("t", ["+" + T, T + "x", T + " 1", "x" + T, T + "\n", "1_784_977_714_054"])
def test_rejects_signed_timestamps_that_are_not_pure_digits(t):
    assert not verify(f"t={t},v1={sign(t)}")


def test_rejects_non_ascii_digits_even_when_signed():
    t = "١" + T[1:]  # ARABIC-INDIC DIGIT ONE: int() accepts it, the signer never writes it
    assert not verify(f"t={t},v1={sign(t)}")


def test_rejects_when_no_v1_matches():
    assert not verify(f"t={T},v1={'0' * 64},v1={'f' * 64}")


def test_rejects_a_wrong_secret():
    assert not verify(f"t={T},v1={V1}", secret="whsec_" + "ab" * 23 + "ac")
    assert not verify(f"t={T},v1={V1}", secret="ab" * 24), "the whsec_ prefix is part of the key"


def test_rejects_a_body_altered_by_one_byte():
    assert not verify(f"t={T},v1={V1}", body='{"id":"evt_2","type":"delivered"}')
    assert not verify(f"t={T},v1={V1}", body=BODY + " ")


def test_rejects_the_body_signed_alone():
    alone = hmac.new(SECRET.encode(), BODY.encode(), hashlib.sha256).hexdigest()
    assert not verify(f"t={T},v1={alone}")


def test_signs_the_timestamp_string_as_received():
    assert not verify(f"t=0001784977714054,v1={V1}")
    assert not verify(f"t=01784977714054,v1={V1}")
    assert verify(f"t=01784977714054,v1={sign('01784977714054')}")


@pytest.mark.parametrize(
    ("skew_ms", "expected"),
    [(-300_000, True), (-300_001, False), (300_000, True), (300_001, False), (-86_400_000, False)],
)
def test_enforces_the_tolerance_both_ways(skew_ms, expected):
    t = str(NOW + skew_ms)
    assert verify(f"t={t},v1={sign(t)}") is expected


def test_tolerance_is_configurable():
    t = str(NOW - 60_001)
    header = f"t={t},v1={sign(t)}"
    assert not verify(header, tolerance=60)
    assert verify(header, tolerance=61)
    assert verify(f"t={T},v1={V1}", tolerance=0), "zero tolerance accepts the same millisecond"


def test_defaults_to_five_minutes_and_the_real_clock():
    now = time.time_ns() // 1_000_000
    fresh, stale, inside = str(now - 1_000), str(now - 310_000), str(now - 290_000)
    assert verify_webhook(BODY, f"t={fresh},v1={sign(fresh)}", SECRET)
    assert not verify_webhook(BODY, f"t={stale},v1={sign(stale)}", SECRET)
    assert verify_webhook(BODY, f"t={inside},v1={sign(inside)}", SECRET)


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "nonsense",
        f"v1={V1}",
        f"t={T}",
        f"t={T},v1=",
        f"t=,v1={V1}",
        f"t=abc,v1={V1}",
        f"t=-{T},v1={V1}",
        f"t={T}.0,v1={V1}",
        f"t=1.784977714054e12,v1={V1}",
        f"t={T}000,v1={V1}",
        f"t={T}\n0,v1={V1}",
        f"t={T},t={T},v1={V1}",
        f"t={T},v1={V1[:63]}",
        f"t={T},v1={V1}0",
        f"t={T};v1={V1}",
        f"t{T},v1={V1}",
        f"t={T},v1=é{V1[1:]}",
    ],
)
def test_rejects_malformed_headers(header):
    assert not verify(header)


def test_configuration_errors_raise():
    with pytest.raises(ValueError, match="secret"):
        verify_webhook(BODY, f"t={T},v1={V1}", "")
    with pytest.raises(ValueError, match="tolerance"):
        verify_webhook(BODY, f"t={T},v1={V1}", SECRET, tolerance_seconds=-1)
