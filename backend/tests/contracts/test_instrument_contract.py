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
    # min_capacity is required (changed from optional this task) — Table 3
    # classification needs it; accuracy_class itself is now optional (it's
    # server-derived), so missing IT no longer raises — see
    # test_instrument_in_accuracy_class_is_optional below.
    bad = {k: v for k, v in _VALID_IN.items() if k != "min_capacity"}
    with pytest.raises(ValidationError):
        InstrumentIn(**bad)


def test_instrument_in_accuracy_class_is_optional():
    # accuracy_class is no longer a required client input — it's derived
    # server-side (app.services.instruments.derive_accuracy_class). Omitting
    # it parses fine; the field only exists to disambiguate when e/Max/Min
    # qualify for more than one class.
    bad = {k: v for k, v in _VALID_IN.items() if k != "accuracy_class"}
    instrument = InstrumentIn(**bad)
    assert instrument.accuracy_class is None


def test_instrument_in_rejects_bad_accuracy_class():
    with pytest.raises(ValidationError):
        InstrumentIn(**dict(_VALID_IN, accuracy_class="V"))


def test_instrument_insert_payload_is_json_safe_and_carries_registered_by():
    instrument = InstrumentIn(**_VALID_IN)
    payload = instrument_insert_payload("user-123", instrument, AccuracyClass.III)
    assert payload["registered_by"] == "user-123"
    assert payload["e_value"] == "1"  # Decimal serialized as a string, not a number
    assert payload["max_capacity"] == "5000"
    assert payload["accuracy_class"] == "III"


def test_instrument_insert_payload_uses_the_passed_accuracy_class_not_the_payload_field():
    # The whole point of taking accuracy_class as an explicit argument: even
    # if the client's own submitted accuracy_class field said something
    # else, the server-derived value passed in here is what gets stored.
    instrument = InstrumentIn(**dict(_VALID_IN, accuracy_class="IIII"))
    payload = instrument_insert_payload("user-123", instrument, AccuracyClass.II)
    assert payload["accuracy_class"] == "II"


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
    row = dict(
        accuracy_class="III", e_value=1.0, max_capacity=5000.0, min_capacity=None,
        indication_type="digital", is_mobile=False, d_value=None,
    )
    params = instrument_params_from_row(row)
    assert params.accuracy_class is AccuracyClass.III
    assert params.e_value == D("1")
    assert params.max_capacity == D("5000")
    assert params.min_capacity is None
    assert params.indication_type.value == "digital"
    assert params.is_mobile is False
    assert params.d_value is None


def test_instrument_params_from_row_carries_indication_type_is_mobile_and_d_value():
    row = dict(
        accuracy_class="II", e_value=1.0, max_capacity=5000.0, min_capacity=10.0,
        indication_type="non_self_indicating", is_mobile=True, d_value=0.5,
    )
    params = instrument_params_from_row(row)
    assert params.indication_type.value == "non_self_indicating"
    assert params.is_mobile is True
    assert params.d_value == D("0.5")


# ---------------------------------------------------------------------------
# R 76-2 page-6 "General information concerning the type" fields — all
# optional, so the core (identity + e/Max/Min) can be submitted alone.
# ---------------------------------------------------------------------------
def test_instrument_in_page_6_fields_are_all_optional():
    instrument = InstrumentIn(**_VALID_IN)
    assert instrument.applicant is None
    assert instrument.printer_status is None
    assert instrument.load_cell_capacity is None


def test_instrument_in_parses_page_6_fields_when_given():
    instrument = InstrumentIn(
        **_VALID_IN,
        applicant="RRSL Mumbai",
        instrument_category="Complete instrument",
        u_nom="230",
        u_min="207",
        u_max="253",
        mains_frequency="50",
        battery_u_nom="9",
        printer_status="built_in",
        zero_device_type="automatic_zero_setting",
        tare_device_type="subtractive_tare",
        initial_zero_setting_range_pct="20",
        temperature_range_min="-10",
        temperature_range_max="40",
        load_cell_manufacturer="HBM",
        load_cell_type="Z6",
        load_cell_capacity="3000",
        load_cell_number="LC-001",
        load_cell_class_symbol="C3",
        software_version="1.2.3",
        identification_no="ID-001",
        interfaces="RS-232 (1x)",
    )
    assert instrument.u_nom == D("230")
    assert instrument.printer_status == "built_in"
    assert instrument.zero_device_type == "automatic_zero_setting"
    assert instrument.tare_device_type == "subtractive_tare"
    assert instrument.temperature_range_min == D("-10")
    assert instrument.load_cell_capacity == D("3000")


def test_instrument_in_rejects_bad_printer_status():
    with pytest.raises(ValidationError):
        InstrumentIn(**_VALID_IN, printer_status="on_fire")


def test_instrument_in_rejects_bad_zero_device_type():
    with pytest.raises(ValidationError):
        InstrumentIn(**_VALID_IN, zero_device_type="not_a_real_option")


def test_instrument_in_rejects_bad_tare_device_type():
    with pytest.raises(ValidationError):
        InstrumentIn(**_VALID_IN, tare_device_type="not_a_real_option")


def test_instrument_in_rejects_float_page_6_numeric_field():
    with pytest.raises(ValidationError):
        InstrumentIn(**_VALID_IN, u_nom=230.0)


def test_instrument_insert_payload_carries_page_6_fields():
    instrument = InstrumentIn(**_VALID_IN, applicant="RRSL Mumbai", u_nom="230", printer_status="built_in")
    payload = instrument_insert_payload("user-123", instrument, AccuracyClass.III)
    assert payload["applicant"] == "RRSL Mumbai"
    assert payload["u_nom"] == "230"  # string, not a JSON number
    assert payload["printer_status"] == "built_in"


def test_instrument_out_from_row_handles_page_6_fields_missing_from_a_pre_migration_row():
    # A row from before db/migrations/002_registration_fields.sql was
    # applied (or simply never filled in) won't have these keys at all —
    # InstrumentOut must still parse, with every page-6 field defaulting to
    # None, not raise on "extra field forbidden" or a missing-field error.
    out = instrument_out_from_row(_RAW_ROW_WITH_FLOATS)
    assert out.applicant is None
    assert out.u_nom is None
    assert out.printer_status is None


def test_instrument_out_from_row_converts_page_6_numeric_floats_from_postgrest():
    row = dict(_RAW_ROW_WITH_FLOATS, u_nom=230.0, load_cell_capacity=3000.0)
    out = instrument_out_from_row(row)
    assert out.u_nom == D("230")
    assert out.load_cell_capacity == D("3000")
