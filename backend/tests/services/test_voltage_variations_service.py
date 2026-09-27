"""Pure unit tests for app.services.voltage_variations — no DB, no HTTP."""

from decimal import Decimal

import pytest

from app.contracts.common import IndicationType
from app.contracts.instrument import InstrumentParams
from app.contracts.voltage_variations import VoltageVariationsReadingSubmitIn
from app.services.voltage_variations import (
    UnknownLevelKey,
    compute_result_for_submission,
    level_index,
    levels_with_mpe,
    load_for,
)
from engine.types import AccuracyClass, VerificationType

D = Decimal

_INSTRUMENT = InstrumentParams(
    accuracy_class=AccuracyClass.III, e_value=D("1"), max_capacity=D("1000"), min_capacity=D("10"),
    indication_type=IndicationType.DIGITAL, is_mobile=False, d_value=None,
)


def test_load_for_is_always_10e():
    assert load_for(_INSTRUMENT) == D("10")
    instrument_e5 = InstrumentParams(
        accuracy_class=AccuracyClass.III, e_value=D("5"), max_capacity=D("1000"), min_capacity=D("10"),
        indication_type=IndicationType.DIGITAL, is_mobile=False, d_value=None,
    )
    assert load_for(instrument_e5) == D("50")


def test_level_index_orders_reference_lower_upper():
    assert level_index("reference") == 0
    assert level_index("lower") == 1
    assert level_index("upper") == 2


def test_level_index_raises_for_unknown_key():
    with pytest.raises(UnknownLevelKey):
        level_index("nominal")


def test_levels_with_mpe_returns_three_levels_same_load():
    levels = levels_with_mpe(_INSTRUMENT, VerificationType.INITIAL)
    assert len(levels) == 3
    assert {level.level_key for level in levels} == {"reference", "lower", "upper"}
    assert all(level.L == D("10") for level in levels)
    # Same load/class/verification_type -> identical mpe band across levels.
    assert len({level.mpe for level in levels}) == 1


def test_submission_computes_correctly_at_10e():
    submission = VoltageVariationsReadingSubmitIn(level_key="reference", U="230", I="10.1", delta_l="0.5", E0="0")
    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)
    assert result.L == D("10")
    assert result.result_out.E == D("0.1")  # I + 1/2e - deltaL - L = 10.1 + 0.5 - 0.5 - 10
    assert result.result_out.Ec == D("0.1")
    assert result.result_out.U == D("230")
    assert result.result_out.passed == (D("0.1") <= result.result_out.mpe)


def test_submission_raises_for_unknown_level_key():
    submission = VoltageVariationsReadingSubmitIn.model_construct(level_key="nominal", U=None, I=D("1"), delta_l=D("0"), E0=D("0"))
    with pytest.raises(UnknownLevelKey):
        compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)


def test_submission_u_is_optional():
    submission = VoltageVariationsReadingSubmitIn(level_key="lower", I="10", delta_l="0", E0="0")
    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)
    assert result.result_out.U is None
