"""Tests for the Weighing Pydantic contracts
(backend/app/contracts/{common,weighing}.py)."""

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.contracts.common import Direction, StrictDecimal
from app.contracts.weighing import (
    WeighingReadingIn,
    WeighingReadingSubmitIn,
    WeighingResultOut,
    WeighingSequenceEntryOut,
    reading_to_engine_kwargs,
    result_to_out,
)
from engine.types import AccuracyClass, VerificationType
from engine.weighing import compute_weighing_result

D = Decimal

_decimal_adapter = TypeAdapter(StrictDecimal)

_VALID_READING = dict(
    accuracy_class="III",
    verification_type="initial",
    direction="up",
    e="1",
    L="300",
    I="300.4",
    delta_l="0.5",
    E0="0",
)


# ---------------------------------------------------------------------------
# Decimal discipline — the critical requirement.
# ---------------------------------------------------------------------------
def test_strict_decimal_string_round_trip_exact():
    value = _decimal_adapter.validate_python("300.6")
    assert value == D("300.6")
    assert _decimal_adapter.dump_json(value).decode() == '"300.6"'


def test_strict_decimal_accepts_int_exactly():
    assert _decimal_adapter.validate_python(300) == D("300")


def test_strict_decimal_rejects_float():
    with pytest.raises(ValidationError):
        _decimal_adapter.validate_python(300.6)


def test_strict_decimal_rejects_garbage_string():
    with pytest.raises(ValidationError):
        _decimal_adapter.validate_python("not-a-number")


def test_strict_decimal_rejects_bool():
    with pytest.raises(ValidationError):
        _decimal_adapter.validate_python(True)


# ---------------------------------------------------------------------------
# WeighingReadingIn.
# ---------------------------------------------------------------------------
def test_valid_reading_parses_with_exact_decimals():
    reading = WeighingReadingIn(**_VALID_READING)
    assert reading.I == D("300.4")
    assert reading.L == D("300")
    assert reading.delta_l == D("0.5")
    assert reading.accuracy_class is AccuracyClass.III
    assert reading.verification_type is VerificationType.INITIAL
    assert reading.direction is Direction.UP


def test_reading_rejects_float_field():
    bad = dict(_VALID_READING, I=300.4)
    with pytest.raises(ValidationError):
        WeighingReadingIn(**bad)


@pytest.mark.parametrize(
    "missing",
    ["accuracy_class", "verification_type", "direction", "e", "L", "I", "delta_l", "E0"],
)
def test_reading_requires_every_field(missing):
    bad = {k: v for k, v in _VALID_READING.items() if k != missing}
    with pytest.raises(ValidationError):
        WeighingReadingIn(**bad)


def test_reading_rejects_bad_accuracy_class():
    bad = dict(_VALID_READING, accuracy_class="V")
    with pytest.raises(ValidationError):
        WeighingReadingIn(**bad)


def test_reading_rejects_bad_verification_type():
    bad = dict(_VALID_READING, verification_type="annual")
    with pytest.raises(ValidationError):
        WeighingReadingIn(**bad)


def test_reading_rejects_bad_direction():
    bad = dict(_VALID_READING, direction="sideways")
    with pytest.raises(ValidationError):
        WeighingReadingIn(**bad)


def test_reading_rejects_unknown_field():
    bad = dict(_VALID_READING, unexpected="nope")
    with pytest.raises(ValidationError):
        WeighingReadingIn(**bad)


# ---------------------------------------------------------------------------
# Adapter seam: WeighingReadingIn -> engine kwargs -> engine result ->
# WeighingResultOut -> JSON. Exact values, never lossy.
# ---------------------------------------------------------------------------
def test_reading_to_result_out_round_trip_pass_case():
    reading = WeighingReadingIn(**_VALID_READING)
    kwargs = reading_to_engine_kwargs(reading)

    result = compute_weighing_result(**kwargs)
    out = result_to_out(result)

    assert out.E == D("0.4")
    assert out.Ec == D("0.4")
    assert out.mpe == D("0.5")
    assert out.passed is True

    dumped = out.model_dump(mode="json")
    assert dumped["E"] == "0.4"
    assert dumped["Ec"] == "0.4"
    assert dumped["mpe"] == "0.5"
    assert dumped["margin"] == "0.1"
    assert dumped["passed"] is True
    for key in ("L", "I", "delta_l", "E0", "E", "Ec", "mpe", "margin", "mpe_in_e", "band_lower_m"):
        assert isinstance(dumped[key], str), f"{key} must serialize as a JSON string, not a number"


def test_reading_to_result_out_round_trip_fail_case_not_lossy():
    reading = WeighingReadingIn(**dict(_VALID_READING, I="300.6"))
    kwargs = reading_to_engine_kwargs(reading)
    result = compute_weighing_result(**kwargs)
    out = result_to_out(result)

    assert out.passed is False
    dumped = out.model_dump(mode="json")
    assert dumped["Ec"] == "0.6"
    assert dumped["passed"] is False


def test_result_out_band_upper_m_null_for_unbounded_top_band():
    # Class I's top band has no upper bound (m > 200000) -> band_upper_m is None.
    reading = WeighingReadingIn(
        **dict(
            _VALID_READING,
            accuracy_class="I",
            L="300000",
            I="300000.4",
            e="1",
            delta_l="0.5",
        )
    )
    kwargs = reading_to_engine_kwargs(reading)
    result = compute_weighing_result(**kwargs)
    out = result_to_out(result)

    assert out.band_upper_m is None
    assert out.model_dump(mode="json")["band_upper_m"] is None


# ---------------------------------------------------------------------------
# Enum parity: the contract enums ARE the engine enums (by construction, not
# by mirroring) — this test locks that design decision in place so a future
# edit can't quietly swap in a copy that drifts.
# ---------------------------------------------------------------------------
def test_contract_enums_are_the_engine_enums_not_a_copy():
    assert WeighingReadingIn.model_fields["accuracy_class"].annotation is AccuracyClass
    assert WeighingReadingIn.model_fields["verification_type"].annotation is VerificationType
    assert WeighingResultOut.model_fields["accuracy_class"].annotation is AccuracyClass
    assert WeighingResultOut.model_fields["verification_type"].annotation is VerificationType


def test_every_engine_accuracy_class_is_a_valid_contract_value():
    for member in AccuracyClass:
        WeighingReadingIn(**dict(_VALID_READING, accuracy_class=member.value, L="1", I="1", delta_l="0", E0="0"))


def test_every_engine_verification_type_is_a_valid_contract_value():
    for member in VerificationType:
        WeighingReadingIn(**dict(_VALID_READING, verification_type=member.value))


# ---------------------------------------------------------------------------
# WeighingReadingSubmitIn / WeighingSequenceEntryOut — the client-facing
# shapes for GET .../sequence and POST .../readings.
# ---------------------------------------------------------------------------
def test_submit_in_parses_without_L_or_instrument_context():
    submission = WeighingReadingSubmitIn(sequence_no=0, direction="up", I="300.4", delta_l="0.5", E0="0")
    assert submission.sequence_no == 0
    assert submission.direction is Direction.UP
    assert not hasattr(submission, "L")


def test_submit_in_rejects_negative_sequence_no():
    with pytest.raises(ValidationError):
        WeighingReadingSubmitIn(sequence_no=-1, direction="up", I="1", delta_l="0", E0="0")


def test_submit_in_rejects_unknown_field_including_L():
    with pytest.raises(ValidationError):
        WeighingReadingSubmitIn(sequence_no=0, direction="up", I="1", delta_l="0", E0="0", L="300")


def test_sequence_entry_out_serializes_kind_and_numbers_as_strings():
    entry = WeighingSequenceEntryOut(sequence_no=0, L="300", m="300", kind="max", mpe="0.5")
    dumped = entry.model_dump(mode="json")
    assert dumped["kind"] == "max"
    assert dumped["L"] == "300"
    assert dumped["sequence_no"] == 0


def test_sequence_entry_out_rejects_bad_kind():
    with pytest.raises(ValidationError):
        WeighingSequenceEntryOut(sequence_no=0, L="300", m="300", kind="sideways", mpe="0.5")
