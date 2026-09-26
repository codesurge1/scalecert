from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.contracts.instrument import (
    InstrumentIn,
    instrument_insert_payload,
    instrument_out_from_row,
    instrument_params_from_row,
)
from engine.types import AccuracyClass

D = Decimal

_VALID_IN = dict(
    accuracy_class="III",
    e_value="1",
    max_capacity="5000",
    min_capacity="10",
    indication_type="digital",
)


def test_valid_instrument_in_parses():
    instrument = InstrumentIn(**_VALID_IN)
    assert instrument.e_value == D("1")
    assert instrument.is_mobile is False
    assert instrument.is_multi_interval is False


def test_instrument_in_rejects_float_field():
    with pytest.raises(ValidationError):
        InstrumentIn(**dict(_VALID_IN, max_capacity=5000.0))


def test_instrument_in_rejects_missing_required_field():
    bad = {k: v for k, v in _VALID_IN.items() if k != "accuracy_class"}
    with pytest.raises(ValidationError):
        InstrumentIn(**bad)


def test_instrument_in_rejects_bad_accuracy_class():
    with pytest.raises(ValidationError):
        InstrumentIn(**dict(_VALID_IN, accuracy_class="V"))


def test_instrument_insert_payload_is_json_safe_and_carries_registered_by():
    instrument = InstrumentIn(**_VALID_IN)
    payload = instrument_insert_payload("user-123", instrument)
    assert payload["registered_by"] == "user-123"
    assert payload["e_value"] == "1"  # Decimal serialized as a string, not a number
    assert payload["max_capacity"] == "5000"


_RAW_ROW_WITH_FLOATS = dict(
    id="i1",
    registered_by="user-123",
    application_no=None,
    type_designation=None,
    manufacturer=None,
    model=None,
    serial_number=None,
    accuracy_class="III",
    e_value=1.0,
    d_value=None,
    max_capacity=5000.0,
    min_capacity=0.1,
    indication_type="digital",
    is_mobile=False,
    is_multi_interval=False,
    created_at="2026-01-01T00:00:00Z",
)


def test_instrument_out_from_row_handles_float_from_postgrest_exactly():
    # Simulates exactly what PostgREST actually returns: numeric columns as
    # JSON numbers (Python float after json-decoding), not strings — the
    # real-world case StrictDecimal's outright float rejection would break
    # if it were applied directly here without this conversion step.
    out = instrument_out_from_row(_RAW_ROW_WITH_FLOATS)
    assert out.e_value == D("1")
    assert out.max_capacity == D("5000")
    assert out.min_capacity == D("0.1")  # exact — not 0.1000000000000000055511151231257827021181583404541015625
    dumped = out.model_dump(mode="json")
    assert dumped["min_capacity"] == "0.1"
    assert dumped["e_value"] == "1.0"  # Decimal(str(1.0)) == Decimal('1.0') — exact, just not canonicalized


def test_instrument_params_from_row_handles_float_and_none_min():
    row = dict(accuracy_class="III", e_value=1.0, max_capacity=5000.0, min_capacity=None)
    params = instrument_params_from_row(row)
    assert params.accuracy_class is AccuracyClass.III
    assert params.e_value == D("1")
    assert params.max_capacity == D("5000")
    assert params.min_capacity is None
