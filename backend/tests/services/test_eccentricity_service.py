"""Pure unit tests for app.services.eccentricity — no DB, no HTTP."""

from decimal import Decimal

from app.contracts.instrument import InstrumentParams
from app.contracts.eccentricity import EccentricityReadingSubmitIn
from app.services.eccentricity import build_load, compute_result_for_submission
from engine.types import AccuracyClass, VerificationType

D = Decimal

_INSTRUMENT = InstrumentParams(
    accuracy_class=AccuracyClass.III,
    e_value=D("1"),
    max_capacity=D("3000"),
    min_capacity=D("10"),
)


def test_build_load_matches_engine_convention():
    assert build_load(_INSTRUMENT) == D("1000")


def test_compute_result_for_submission_end_to_end_pure():
    L = build_load(_INSTRUMENT)
    submission = EccentricityReadingSubmitIn(
        position_no=1,
        I=str(L + D("0.1")),
        delta_l="0.5",  # = e/2, cancels the engine's +1/2e term
        E0="0",
    )
    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)

    assert result.L == L
    assert result.reading.position_no == 1
    assert result.result_out.position_no == 1
    assert result.result_out.E == D("0.1")
    assert result.result_out.Ec == D("0.1")
    assert result.result_out.passed == (D("0.1") <= result.result_out.mpe)


def test_compute_result_for_submission_e0_is_independent_per_call():
    submission_1 = EccentricityReadingSubmitIn(position_no=1, I="1000.4", delta_l="0.5", E0="0")
    submission_2 = EccentricityReadingSubmitIn(position_no=2, I="1000.4", delta_l="0.5", E0="0.3")

    result_1 = compute_result_for_submission(submission_1, _INSTRUMENT, VerificationType.INITIAL)
    result_2 = compute_result_for_submission(submission_2, _INSTRUMENT, VerificationType.INITIAL)

    assert result_1.result_out.E == result_2.result_out.E
    assert result_2.result_out.Ec == result_1.result_out.Ec - D("0.3")
