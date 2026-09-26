"""engine/zero_tare.py — the zero/tare device accuracy variant of Weighing.
Reuses compute_weighing_result's own boundary behavior (already proven by
tests/test_mpe_boundaries.py and tests/test_worked_example.py) — these tests
cover the two things unique to this module: the check-load generator, and
that the wrapper genuinely delegates rather than silently diverging.
"""

from decimal import Decimal

import pytest

from engine.types import AccuracyClass, VerificationType
from engine.weighing import compute_weighing_result
from engine.zero_tare import compute_zero_tare_result, generate_zero_tare_checks

D = Decimal


def test_generate_zero_tare_checks_uses_min_capacity_as_anchor_when_given():
    checks = generate_zero_tare_checks(max_capacity=D("6000"), min_capacity=D("20"))
    assert checks == [D("0"), D("20"), D("40")]


def test_generate_zero_tare_checks_falls_back_to_fraction_of_max_without_min_capacity():
    checks = generate_zero_tare_checks(max_capacity=D("6000"), min_capacity=None)
    assert checks[0] == D("0")
    assert checks[1] == D("6000") * D("0.05")
    assert checks[2] == checks[1] * 2


def test_generate_zero_tare_checks_always_starts_at_zero():
    checks = generate_zero_tare_checks(max_capacity=D("100"), min_capacity=D("5"))
    assert checks[0] == D("0")


def test_generate_zero_tare_checks_rejects_non_decimal_max_capacity():
    with pytest.raises(TypeError):
        generate_zero_tare_checks(max_capacity=6000.0, min_capacity=None)


def test_generate_zero_tare_checks_rejects_non_positive_max_capacity():
    with pytest.raises(ValueError):
        generate_zero_tare_checks(max_capacity=D("0"), min_capacity=None)


def test_generate_zero_tare_checks_rejects_non_decimal_min_capacity():
    with pytest.raises(TypeError):
        generate_zero_tare_checks(max_capacity=D("6000"), min_capacity=20.0)


def test_generate_zero_tare_checks_rejects_negative_min_capacity():
    with pytest.raises(ValueError):
        generate_zero_tare_checks(max_capacity=D("6000"), min_capacity=D("-1"))


def test_generate_zero_tare_checks_treats_zero_min_capacity_as_unknown():
    # min_capacity=0 isn't a meaningful anchor (nothing to weigh) — falls back
    # exactly like None.
    with_zero = generate_zero_tare_checks(max_capacity=D("6000"), min_capacity=D("0"))
    with_none = generate_zero_tare_checks(max_capacity=D("6000"), min_capacity=None)
    assert with_zero == with_none


_WEIGHING_KWARGS = dict(
    accuracy_class=AccuracyClass.III,
    verification_type=VerificationType.INITIAL,
    e=D("1"),
    L=D("20"),
    I=D("20.4"),
    delta_l=D("0.5"),
    E0=D("0"),
)


def test_compute_zero_tare_result_delegates_exactly_to_compute_weighing_result():
    zero_tare = compute_zero_tare_result(**_WEIGHING_KWARGS)
    weighing = compute_weighing_result(**_WEIGHING_KWARGS)
    assert zero_tare == weighing


def test_compute_zero_tare_result_pass_and_fail_at_the_mpe_boundary():
    # e=1g, m=20 -> Band 1 (Class III, m<=500) -> mpe = 0.5g.
    passing = compute_zero_tare_result(**dict(_WEIGHING_KWARGS, I=D("20.4"), delta_l=D("0.5")))
    assert passing.mpe == D("0.5")
    assert passing.Ec == D("0.4")
    assert passing.passed is True

    failing = compute_zero_tare_result(**dict(_WEIGHING_KWARGS, I=D("20.6"), delta_l=D("0.5")))
    assert failing.Ec == D("0.6")
    assert failing.passed is False


def test_compute_zero_tare_result_requires_every_argument():
    for missing in _WEIGHING_KWARGS:
        kwargs = {k: v for k, v in _WEIGHING_KWARGS.items() if k != missing}
        with pytest.raises(TypeError):
            compute_zero_tare_result(**kwargs)
