"""Shared contract-layer building blocks: the strict-Decimal type every
numeric field in a Weighing (and later, other test-type) contract uses, and
the one enum the engine doesn't define but the API layer needs.

`accuracy_class` and `verification_type` are deliberately NOT mirrored here.
Every contract imports `engine.types.AccuracyClass` / `VerificationType`
directly as its field type, so there is exactly one source of truth — an API
value and an engine value can never drift apart, because they're the same
Python object, not a copy kept in sync by hand.
"""

from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Annotated, Any

from pydantic import BeforeValidator, PlainSerializer


class Direction(str, Enum):
    """Bidirectional testing (docs/architecture.md, Load-sequence generator):
    each generated load is read going up and coming back down. The engine
    itself is direction-agnostic — it just computes one reading's error —
    so this is purely an API/reading-layer concept and lives here, not in
    engine/.
    """

    UP = "up"
    DOWN = "down"


class IndicationType(str, Enum):
    """Mirrors db/schema.sql's `indication_type` enum. The engine has no use
    for this (it doesn't affect the Weighing calculation), so — unlike
    accuracy_class/verification_type — there is no engine enum to reuse."""

    DIGITAL = "digital"
    ANALOG = "analog"
    NON_SELF_INDICATING = "non_self_indicating"


class SessionStatus(str, Enum):
    """Mirrors db/schema.sql's `session_status` enum."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    RETURNED = "returned"
    APPROVED = "approved"
    ISSUED = "issued"
    SUPERSEDED = "superseded"


class TestType(str, Enum):
    """Mirrors db/schema.sql's `test_type` enum."""

    __test__ = False  # not a pytest test class — its name just starts with "Test"

    WEIGHING = "weighing"
    REPEATABILITY = "repeatability"
    ECCENTRICITY = "eccentricity"
    DISCRIMINATION = "discrimination"
    TILTING = "tilting"
    SENSITIVITY = "sensitivity"


def _parse_strict_decimal(value: Any) -> Decimal:
    """Parse a JSON string or int into an exact Decimal. A bare float is
    REJECTED outright, not coerced — an unquoted float literal in JSON
    (e.g. `300.6`) is exactly the risk this contract layer exists to close
    off: it can silently disagree with the intended decimal value at a
    boundary. Send numeric fields as a JSON string (preferred) or an int.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):  # bool is an int subclass — exclude explicitly
        raise ValueError("a boolean is not a valid Decimal input")
    if isinstance(value, float):
        raise ValueError(
            "float is not accepted for this field — pass a JSON string (preferred) "
            "or an int, never a bare float literal; a float can silently disagree "
            "with the exact decimal value at a boundary."
        )
    if isinstance(value, (str, int)):
        try:
            return Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(f"{value!r} is not a valid decimal number") from exc
    raise ValueError(f"cannot parse {type(value).__name__} as Decimal")


StrictDecimal = Annotated[
    Decimal,
    BeforeValidator(_parse_strict_decimal),
    PlainSerializer(lambda value: str(value), return_type=str, when_used="json"),
]
"""A Decimal field that: accepts a JSON string (preferred) or an int; rejects
a bare float outright (see `_parse_strict_decimal`); and serializes back to a
JSON string, never a JSON number, so nothing downstream can round it through
float either.
"""
