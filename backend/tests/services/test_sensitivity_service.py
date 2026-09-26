"""Pure unit tests for app.services.sensitivity — no DB, no HTTP."""

from decimal import Decimal

import pytest

from app.contracts.common import IndicationType
from app.contracts.instrument import InstrumentParams
from app.contracts.sensitivity import SensitivityReadingSubmitIn
from app.services.sensitivity import (
    SequenceNumberOutOfRange,
    build_checks,
    checks_with_mpe,
    compute_result_for_submission,
)
from engine.types import AccuracyClass, VerificationType

D = Decimal

_INSTRUMENT = InstrumentParams(
    accuracy_class=AccuracyClass.III, e_value=D("1"), max_capacity=D("1000"), min_capacity=D("10"),
    indication_type=IndicationType.NON_SELF_INDICATING, is_mobile=False, d_value=None,
)


def test_build_checks_returns_three_entries():
    assert build_checks(_INSTRUMENT) == [D("10"), D("500"), D("1000")]


def test_checks_with_mpe_includes_threshold_mm_per_check():
    checks = checks_with_mpe(_INSTRUMENT, VerificationType.INITIAL)
    assert len(checks) == 3
    assert all(check.threshold_mm == D("2") for check in checks)  # Class III, Max=1000g <= 30000g


def test_sequence_number_out_of_range_raises():
    with pytest.raises(SequenceNumberOutOfRange):
        compute_result_for_submission(
            SensitivityReadingSubmitIn(sequence_no=99, permanent_displacement_mm=D("2")),
            _INSTRUMENT, VerificationType.INITIAL,
        )


def test_submission_computes_correctly():
    submission = SensitivityReadingSubmitIn(sequence_no=1, permanent_displacement_mm=D("2.5"))
    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)
    assert result.L == D("500")
    assert result.result_out.threshold_mm == D("2")
    assert result.result_out.passed is True


def test_submission_fails_under_threshold():
    submission = SensitivityReadingSubmitIn(sequence_no=1, permanent_displacement_mm=D("1.9"))
    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)
    assert result.result_out.passed is False


def test_submission_uses_5mm_tier_for_high_max_class_3():
    # e=5g (not 1g) so m = Max/e = 8000 stays within Class III's own valid
    # Table 6 range (n_max=10000) while Max itself (40000g = 40kg) still
    # exceeds the 30kg sensitivity-tier boundary.
    instrument = InstrumentParams(
        accuracy_class=AccuracyClass.III, e_value=D("5"), max_capacity=D("40000"), min_capacity=D("100"),
        indication_type=IndicationType.NON_SELF_INDICATING, is_mobile=False, d_value=None,
    )
    submission = SensitivityReadingSubmitIn(sequence_no=2, permanent_displacement_mm=D("4.9"))
    result = compute_result_for_submission(submission, instrument, VerificationType.INITIAL)
    assert result.result_out.threshold_mm == D("5")
    assert result.result_out.passed is False
