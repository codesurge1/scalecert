"""engine/eccentricity.py — same change-point math as Weighing, applied
independently at each of 4 positions with its OWN E0 (re-measured before
each position, never a shared baseline). These tests cover the load
generator, position-number validation, that the wrapper genuinely delegates
to compute_weighing_result, and — the one thing actually unique to this
module — that per-position E0 is truly independent (two positions with
different E0 but identical I/L/delta_l produce different Ec/passed, proving
there's no shared/global zero state).
"""

from decimal import Decimal

import pytest

from engine.eccentricity import (
    ECCENTRICITY_POSITIONS,
    compute_eccentricity_position,
    generate_eccentricity_load,
)
from engine.types import AccuracyClass, VerificationType
from engine.weighing import compute_weighing_result

D = Decimal


def test_generate_eccentricity_load_is_one_third_of_max():
    assert generate_eccentricity_load(max_capacity=D("3000")) == D("1000")


def test_generate_eccentricity_load_rejects_non_decimal_max_capacity():
    with pytest.raises(TypeError):
        generate_eccentricity_load(max_capacity=3000.0)


def test_generate_eccentricity_load_rejects_non_positive_max_capacity():
    with pytest.raises(ValueError):
        generate_eccentricity_load(max_capacity=D("0"))


def test_eccentricity_positions_are_1_through_4():
    assert ECCENTRICITY_POSITIONS == (1, 2, 3, 4)


_BASE_KWARGS = dict(
    accuracy_class=AccuracyClass.III,
    verification_type=VerificationType.INITIAL,
    e=D("1"),
    L=D("1000"),
    I=D("1000.4"),
    delta_l=D("0.5"),
    E0=D("0"),
)


@pytest.mark.parametrize("position_no", [1, 2, 3, 4])
def test_compute_eccentricity_position_accepts_every_valid_position(position_no):
    result = compute_eccentricity_position(position_no=position_no, **_BASE_KWARGS)
    assert result.position_no == position_no


@pytest.mark.parametrize("position_no", [0, 5, -1])
def test_compute_eccentricity_position_rejects_invalid_position_numbers(position_no):
    with pytest.raises(ValueError):
        compute_eccentricity_position(position_no=position_no, **_BASE_KWARGS)


def test_compute_eccentricity_position_delegates_exactly_to_compute_weighing_result():
    wrapped = compute_eccentricity_position(position_no=1, **_BASE_KWARGS)
    direct = compute_weighing_result(**_BASE_KWARGS)
    assert wrapped.weighing_result == direct


def test_compute_eccentricity_position_pass_and_fail_at_the_mpe_boundary():
    # e=1g, m=1000 -> Band 2 for Class III (500 < m <= 2000) -> mpe=1.0g.
    passing = compute_eccentricity_position(position_no=1, **dict(_BASE_KWARGS, I=D("1001.0"), delta_l=D("0.5")))
    assert passing.weighing_result.mpe == D("1.0")
    assert passing.weighing_result.Ec == D("1.0")
    assert passing.weighing_result.passed is True

    failing = compute_eccentricity_position(position_no=1, **dict(_BASE_KWARGS, I=D("1001.01"), delta_l=D("0.5")))
    assert failing.weighing_result.Ec == D("1.01")
    assert failing.weighing_result.passed is False


def test_e0_is_independent_per_position_not_a_shared_baseline():
    # Identical I/L/delta_l at two positions, but different E0 — if E0 were
    # ever accidentally shared/global, these would produce the same Ec.
    # They must not.
    position_1 = compute_eccentricity_position(position_no=1, **dict(_BASE_KWARGS, E0=D("0")))
    position_2 = compute_eccentricity_position(position_no=2, **dict(_BASE_KWARGS, E0=D("0.3")))

    assert position_1.weighing_result.E == position_2.weighing_result.E  # same raw E (same I/L/delta_l)
    assert position_1.weighing_result.Ec != position_2.weighing_result.Ec
    assert position_2.weighing_result.Ec == position_1.weighing_result.Ec - D("0.3")


def test_compute_eccentricity_position_requires_every_argument():
    for missing in list(_BASE_KWARGS) + ["position_no"]:
        kwargs = dict(_BASE_KWARGS, position_no=1)
        del kwargs[missing]
        with pytest.raises(TypeError):
            compute_eccentricity_position(**kwargs)
