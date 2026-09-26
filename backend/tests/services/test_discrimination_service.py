"""Pure unit tests for app.services.discrimination — no DB, no HTTP."""

from decimal import Decimal

import pytest

from app.contracts.common import IndicationType
from app.contracts.discrimination import DiscriminationReadingSubmitIn
from app.contracts.instrument import InstrumentParams
from app.services.discrimination import (
    MissingFieldsForVariant,
    SequenceNumberOutOfRange,
    build_checks,
    checks_with_mpe,
    compute_result_for_submission,
    variant_for_instrument,
)
from engine.types import AccuracyClass, VerificationType

D = Decimal


def _instrument(indication_type, **overrides):
    defaults = dict(
        accuracy_class=AccuracyClass.III, e_value=D("1"), max_capacity=D("6000"), min_capacity=D("20"),
        indication_type=indication_type, is_mobile=False, d_value=None,
    )
    defaults.update(overrides)
    return InstrumentParams(**defaults)


_ANALOG = _instrument(IndicationType.ANALOG)
_NON_SELF_INDICATING = _instrument(IndicationType.NON_SELF_INDICATING)
_DIGITAL = _instrument(IndicationType.DIGITAL)


def test_variant_for_instrument_maps_indication_type_correctly():
    assert variant_for_instrument(_ANALOG) == "analog"
    assert variant_for_instrument(_NON_SELF_INDICATING) == "non_self_indicating"
    assert variant_for_instrument(_DIGITAL) == "digital"


def test_build_checks_returns_three_entries():
    assert len(build_checks(_ANALOG)) == 3


def test_checks_with_mpe_has_no_mpe_for_digital_variant():
    checks = checks_with_mpe(_DIGITAL, VerificationType.INITIAL)
    assert all(check.mpe is None for check in checks)
    assert all(check.variant == "digital" for check in checks)


def test_checks_with_mpe_has_mpe_for_analog_and_non_self_indicating():
    analog_checks = checks_with_mpe(_ANALOG, VerificationType.INITIAL)
    nsi_checks = checks_with_mpe(_NON_SELF_INDICATING, VerificationType.INITIAL)
    assert all(check.mpe is not None for check in analog_checks)
    assert all(check.mpe is not None for check in nsi_checks)


def test_check_load_out_of_range_raises():
    with pytest.raises(SequenceNumberOutOfRange):
        compute_result_for_submission(
            DiscriminationReadingSubmitIn(sequence_no=99, I1=D("1"), I2=D("2")),
            _ANALOG, VerificationType.INITIAL,
        )


def test_analog_submission_computes_correctly():
    checks = build_checks(_ANALOG)
    L = checks[0]
    submission = DiscriminationReadingSubmitIn(sequence_no=0, I1=L, I2=L + D("1"))
    result = compute_result_for_submission(submission, _ANALOG, VerificationType.INITIAL)
    assert result.variant == "analog"
    assert result.result_out.difference == D("1")
    assert result.reading_data == {"I1": str(L), "I2": str(L + D("1"))}


def test_analog_submission_requires_i1_and_i2():
    submission = DiscriminationReadingSubmitIn(sequence_no=0, I1=None, I2=None)
    with pytest.raises(MissingFieldsForVariant):
        compute_result_for_submission(submission, _ANALOG, VerificationType.INITIAL)


def test_non_self_indicating_submission_requires_visible_displacement():
    submission = DiscriminationReadingSubmitIn(sequence_no=0)
    with pytest.raises(MissingFieldsForVariant):
        compute_result_for_submission(submission, _NON_SELF_INDICATING, VerificationType.INITIAL)


def test_non_self_indicating_submission_computes_correctly():
    submission = DiscriminationReadingSubmitIn(sequence_no=0, visible_displacement=True)
    result = compute_result_for_submission(submission, _NON_SELF_INDICATING, VerificationType.INITIAL)
    assert result.variant == "non_self_indicating"
    assert result.result_out.passed is True
    assert result.reading_data == {"visible_displacement": True}


def test_digital_submission_uses_d_value_when_present():
    instrument = _instrument(IndicationType.DIGITAL, d_value=D("2"))
    checks = build_checks(instrument)
    submission = DiscriminationReadingSubmitIn(sequence_no=0, I1=checks[0], I2=checks[0] + D("2"))
    result = compute_result_for_submission(submission, instrument, VerificationType.INITIAL)
    assert result.result_out.d == D("2")
    assert result.result_out.passed is True


def test_digital_submission_falls_back_to_e_value_when_no_d_value():
    submission = DiscriminationReadingSubmitIn(sequence_no=0, I1=D("0"), I2=D("1"))
    result = compute_result_for_submission(submission, _DIGITAL, VerificationType.INITIAL)
    assert result.result_out.d == _DIGITAL.e_value


def test_digital_submission_requires_i1_and_i2():
    submission = DiscriminationReadingSubmitIn(sequence_no=0)
    with pytest.raises(MissingFieldsForVariant):
        compute_result_for_submission(submission, _DIGITAL, VerificationType.INITIAL)
