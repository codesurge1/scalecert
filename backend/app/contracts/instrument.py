"""Pydantic v2 contracts for `instruments` (a resource contract, not a
test_type contract — see app/contracts/__init__.py)."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.contracts.common import IndicationType, StrictDecimal
from app.db_decimal import decimal_from_db_value
from engine.types import AccuracyClass


class InstrumentIn(BaseModel):
    """What a client submits to register an instrument. Field names mirror
    db/schema.sql's `instruments` columns directly (`e_value`/`d_value`, not
    the engine's shorter `e`) since this contract's job is to validate what
    gets inserted into that table, not to feed the engine.

    `accuracy_class` is NOT a free client choice — it's derived server-side
    from e_value/max_capacity/min_capacity via
    engine.classification.classify_instrument
    (app.services.instruments.derive_accuracy_class), the same "server
    derives it, the client never invents it" shape as the Weighing load
    sequence's `L` (CLAUDE.md). It stays on this contract ONLY as an
    optional disambiguation hint for the rare case where those values
    qualify for more than one accuracy class — see derive_accuracy_class.
    When exactly one class qualifies this field is ignored entirely.

    `min_capacity` is REQUIRED (changed from optional) because OIML R76-1
    Table 3 classification needs it — every class row carries its own
    Min-capacity requirement, so classification cannot run without it. This
    is a genuinely different question from engine.load_sequence's Min,
    which is optional for an unrelated reason (whether Min is tested as a
    verification anchor, not whether it's known).
    """

    model_config = ConfigDict(extra="forbid")

    application_no: Optional[str] = None
    type_designation: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None

    accuracy_class: Optional[AccuracyClass] = None
    e_value: StrictDecimal
    d_value: Optional[StrictDecimal] = None
    max_capacity: StrictDecimal
    min_capacity: StrictDecimal
    indication_type: IndicationType
    is_mobile: bool = False
    is_multi_interval: bool = False


class InstrumentOut(BaseModel):
    """An `instruments` row as returned to the client — numbers as strings."""

    model_config = ConfigDict(extra="forbid")

    id: str
    registered_by: str
    application_no: Optional[str] = None
    type_designation: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None

    accuracy_class: AccuracyClass
    e_value: StrictDecimal
    d_value: Optional[StrictDecimal] = None
    max_capacity: StrictDecimal
    min_capacity: Optional[StrictDecimal] = None
    indication_type: IndicationType
    is_mobile: bool
    is_multi_interval: bool
    created_at: str


@dataclass(frozen=True)
class InstrumentParams:
    """The subset of an `instruments` row the Weighing engine and the
    load-sequence generator need — a narrower, engine-facing shape than the
    full `InstrumentOut`, so services/weighing.py doesn't have to depend on
    every descriptive field an instrument row happens to carry."""

    accuracy_class: AccuracyClass
    e_value: Decimal
    max_capacity: Decimal
    min_capacity: Optional[Decimal]


_NUMERIC_FIELDS = ("e_value", "d_value", "max_capacity", "min_capacity")


def instrument_out_from_row(row: dict) -> InstrumentOut:
    """Build InstrumentOut from a raw Supabase/PostgREST row.

    `numeric` columns come back from PostgREST as JSON numbers (Python
    `float`), not strings. Converted here via `decimal_from_db_value`
    (app.db_decimal — the DB-row-safe policy) BEFORE the value ever reaches
    `StrictDecimal`'s validator, which exists to reject a float from an
    untrusted CLIENT, not from our own trusted DB response. Passing a raw
    float straight into `InstrumentOut(**row)` would incorrectly trip that
    rejection on every normal read.
    """
    processed = dict(row)
    for field in _NUMERIC_FIELDS:
        if processed.get(field) is not None:
            processed[field] = decimal_from_db_value(processed[field])
    return InstrumentOut(**processed)


def instrument_insert_payload(registered_by: str, payload: InstrumentIn, accuracy_class: AccuracyClass) -> dict:
    """InstrumentIn -> the dict handed to `.table("instruments").insert()`.
    `model_dump(mode="json")` already turns every Decimal into a string (the
    same serializer proven in the Weighing contract tests), so this payload
    is JSON-safe without any extra conversion.

    `accuracy_class` is passed explicitly — the SERVER-DERIVED class from
    `app.services.instruments.derive_accuracy_class`, never
    `payload.accuracy_class` directly: that field only disambiguates when
    e/Max/Min qualify for more than one class (see InstrumentIn's
    docstring) and must never be trusted as the class to store on its own.
    """
    data = payload.model_dump(mode="json", exclude={"accuracy_class"})
    data["accuracy_class"] = accuracy_class.value
    data["registered_by"] = registered_by
    return data


def instrument_params_from_row(row: dict) -> InstrumentParams:
    """Build the engine-facing `InstrumentParams` from a raw instrument row —
    same float-from-PostgREST handling as `instrument_out_from_row`."""
    return InstrumentParams(
        accuracy_class=AccuracyClass(row["accuracy_class"]),
        e_value=decimal_from_db_value(row["e_value"]),
        max_capacity=decimal_from_db_value(row["max_capacity"]),
        min_capacity=(
            decimal_from_db_value(row["min_capacity"]) if row.get("min_capacity") is not None else None
        ),
    )
