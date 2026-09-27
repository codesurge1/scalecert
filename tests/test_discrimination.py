"""engine/discrimination.py — three distinct sub-procedures, not variants of
one formula: analog (threshold on I2-I1 vs 0.7*mpe), non-self-indicating
(qualitative Yes/No), and digital (threshold on I2-I1 vs d, no mpe at all).
"""

from decimal import Decimal

import pytest

from engine.discrimination import (
    compute_discrimination_analog,
    compute_discrimination_digital,
    compute_discrimination_non_self_indicating,
    generate_discrimination_checks,
)
from engine.types import AccuracyClass, VerificationType

D = Decimal

_CLASS = AccuracyClass.III
_VTYPE = VerificationType.INITIAL
_E = D("1")
_L = D("500")  # m=500 -> Band 1 for Class III -> mpe=0.5g


def test_generate_discrimination_checks_uses_min_capacity_as_low_anchor():
    checks = generate_discrimination_checks(max_capacity=D("6000"), min_capacity=D("20"))
    assert checks == [D("20"), D("3000"), D("6000")]


def test_generate_discrimination_checks_falls_back_without_min_capacity():
    checks = generate_discrimination_checks(max_capacity=D("6000"), min_capacity=None)
    assert checks[0] == D("6000") * D("0.1")
    assert checks[1] == D("3000")
    assert checks[2] == D("6000")


def test_generate_discrimination_checks_rejects_non_decimal_max_capacity():
    with pytest.raises(TypeError):
        generate_discrimination_checks(max_capacity=6000.0, min_capacity=None)


def test_generate_discrimination_checks_rejects_non_positive_max_capacity():
    with pytest.raises(ValueError):
        generate_discrimination_checks(max_capacity=D("0"), min_capacity=None)


# --- Analog (A.4.8.1) ---


def test_analog_passes_at_the_threshold_boundary_inclusive():
    # mpe=0.5g -> threshold = 0.7*0.5 = 0.35g exactly.
    result = compute_discrimination_analog(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=_L, I1=D("500"), I2=D("500.35"))
    assert result.mpe == D("0.5")
    assert result.threshold == D("0.35")
    assert result.difference == D("0.35")
    assert result.passed is True


def test_analog_fails_just_under_threshold():
    result = compute_discrimination_analog(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=_L, I1=D("500"), I2=D("500.34"))
    assert result.passed is False


def test_analog_requires_every_argument():
    kwargs = dict(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=_L, I1=D("500"), I2=D("500.4"))
    for missing in kwargs:
        bad = {k: v for k, v in kwargs.items() if k != missing}
        with pytest.raises(TypeError):
            compute_discrimination_analog(**bad)


def test_analog_rejects_negative_load():
    with pytest.raises(ValueError):
        compute_discrimination_analog(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("-1"), I1=D("0"), I2=D("1"))


# --- Non-self-indicating (A.4.8.1) ---


def test_non_self_indicating_extra_load_is_0_4_of_mpe():
    result = compute_discrimination_non_self_indicating(
        accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=_L, visible_displacement=True
    )
    assert result.mpe == D("0.5")
    assert result.extra_load == D("0.5") * D("0.4")


def test_non_self_indicating_passes_iff_displacement_observed():
    passing = compute_discrimination_non_self_indicating(
        accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=_L, visible_displacement=True
    )
    assert passing.passed is True

    failing = compute_discrimination_non_self_indicating(
        accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=_L, visible_displacement=False
    )
    assert failing.passed is False


def test_non_self_indicating_rejects_non_bool_displacement():
    with pytest.raises(TypeError):
        compute_discrimination_non_self_indicating(
            accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=_L, visible_displacement="yes"
        )


# --- Digital (A.4.8.2) — no mpe/accuracy_class/verification_type involved ---


def test_digital_passes_at_the_d_boundary_inclusive():
    result = compute_discrimination_digital(L=_L, d=D("1"), I1=D("500"), I2=D("501"))
    assert result.difference == D("1")
    assert result.passed is True


def test_digital_fails_just_under_d():
    result = compute_discrimination_digital(L=_L, d=D("1"), I1=D("500"), I2=D("500.9"))
    assert result.passed is False


def test_digital_rejects_non_positive_d():
    with pytest.raises(ValueError):
        compute_discrimination_digital(L=_L, d=D("0"), I1=D("500"), I2=D("501"))


def test_digital_rejects_float_instead_of_decimal():
    with pytest.raises(TypeError):
        compute_discrimination_digital(L=_L, d=1.0, I1=D("500"), I2=D("501"))


def test_digital_does_not_require_accuracy_class_or_verification_type():
    # No TypeError for omitting them — the digital sub-procedure genuinely
    # has no mpe lookup at all.
    result = compute_discrimination_digital(L=D("0"), d=D("0.5"), I1=D("0"), I2=D("1"))
    assert result.passed is True
