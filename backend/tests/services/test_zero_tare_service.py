"""Pure unit tests for app.services.zero_tare — no DB, no HTTP."""

from decimal import Decimal

import pytest

from app.contracts.common import IndicationType
from app.contracts.instrument import InstrumentParams
from app.contracts.zero_tare import ZeroTareReadingSubmitIn
from app.services.zero_tare import (
    SequenceNumberOutOfRange,
    build_checks,
    check_load_for_sequence_no,
    compute_result_for_submission,
)
from engine.types import AccuracyClass, VerificationType

D = Decimal

_INSTRUMENT = InstrumentParams(
    accuracy_class=AccuracyClass.III,
    e_value=D("1"),
    max_capacity=D("6000"),
    min_capacity=D("20"),
    indication_type=IndicationType.DIGITAL,
    is_mobile=False,
    d_value=None,
)


def test_build_checks_returns_three_entries_starting_at_zero():
    checks = build_checks(_INSTRUMENT)
    assert len(checks) == 3
    assert checks[0] == D("0")


def test_check_load_for_sequence_no_valid_index():
    checks = build_checks(_INSTRUMENT)
    assert check_load_for_sequence_no(checks, 0) == checks[0]
    assert check_load_for_sequence_no(checks, 2) == checks[2]


@pytest.mark.parametrize("bad_index", [-1, 3, 9999])
def test_check_load_for_sequence_no_out_of_range(bad_index):
    checks = build_checks(_INSTRUMENT)
    with pytest.raises(SequenceNumberOutOfRange):
        check_load_for_sequence_no(checks, bad_index)


def test_compute_result_for_submission_end_to_end_pure():
    checks = build_checks(_INSTRUMENT)
    L = checks[1]  # the min_capacity-anchored check

    submission = ZeroTareReadingSubmitIn(
        sequence_no=1,
        I=str(L + D("0.1")),
        delta_l="0.5",  # = e/2, cancels the engine's +1/2e term -> E = I - L
        E0="0",
    )
    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)

    assert result.L == L
    assert result.reading.L == L
    assert result.result_out.E == D("0.1")
    assert result.result_out.Ec == D("0.1")
    assert result.result_out.passed == (D("0.1") <= result.result_out.mpe)


def test_compute_result_for_submission_raises_for_out_of_range_sequence_no():
    submission = ZeroTareReadingSubmitIn(sequence_no=3, I="1", delta_l="0", E0="0")
    with pytest.raises(SequenceNumberOutOfRange):
        compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)
