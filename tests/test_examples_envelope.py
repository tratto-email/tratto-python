"""Guard: examples must read responses through the ``{"data": …}`` envelope.

Ruff and mypy cannot see this. Every resource method is typed ``-> dict``,
which is ``dict[Any, Any]``, so `email["stauts"]` typechecks perfectly — and
that is exactly how ten examples and the smoke script shipped reading fields
straight off the return value (tratto-python#27). Only running them found it.

This is a narrow guard, and worth naming what it does *not* do: it checks the
envelope, not the field names inside it. A wrong key under ``data`` still gets
through, and only `scripts/staging_smoke.py` against the real API catches that.
"""

import ast
from pathlib import Path

import pytest

# Top-level keys a response legitimately has: the payload, and the cursor block
# that sits beside it on list endpoints.
ENVELOPE_KEYS = {"data", "pagination"}

ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted(ROOT.glob("examples/*.py")) + [ROOT / "scripts" / "staging_smoke.py"]


def _is_sdk_call(node: ast.AST) -> bool:
    """True for ``tratto.<resource>.<method>(...)``."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "tratto"
    )


def _key(node: ast.Subscript) -> object:
    return getattr(node.slice, "value", None)


def _offences(source: str) -> list[str]:
    tree = ast.parse(source)
    found: list[str] = []

    # Variables holding a whole, still-wrapped response.
    wrapped: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if _is_sdk_call(node.value):
                wrapped[name] = node.lineno
            else:
                wrapped.pop(name, None)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        key = _key(node)
        if key in ENVELOPE_KEYS:
            continue
        # Either read straight off the call, or off a variable still holding
        # the whole response.
        if _is_sdk_call(node.value) or (
            isinstance(node.value, ast.Name)
            and node.value.id in wrapped
            and node.lineno > wrapped[node.value.id]
        ):
            found.append(f"line {node.lineno}: {ast.unparse(node)}")
    return found


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_example_reads_go_through_the_envelope(path: Path) -> None:
    offences = _offences(path.read_text())
    assert not offences, (
        f"{path.relative_to(ROOT)} reads a field straight off an SDK response. "
        f'The payload is under ["data"]: ' + "; ".join(offences)
    )


def test_the_guard_catches_a_bad_read() -> None:
    """The guard must fail on the exact shape that got through last time."""
    bad = "contact = tratto.contacts.create(options)\nprint(contact['id'])\n"
    assert _offences(bad), "guard is blind to a raw read — it would pass on anything"
    good = "contact = tratto.contacts.create(options)\nprint(contact['data']['id'])\n"
    assert not _offences(good), "guard flags a correct read"
