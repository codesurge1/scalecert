"""engine/tilting.py — the minimal 8.3.3/4.18 slice: reference + 4 tilted
positions, unloaded (establishes each position's own E0) then two loaded
rows (mid load, Max), each loaded row getting its own mpe. These tests
cover: that the unloaded/loaded readings genuinely delegate to
compute_weighing_result (L=0/E0=0 for unloaded; the position's own E0
carried into the loaded reading), the two independent pass criteria at
their inclusive boundary, that E0 is measured once per position and reused
across both loaded rows (not re-measured), and that the two loaded rows can
get different mpe (different Table 6 bands).
"""

from decimal import Decimal

import pytest

from engine.tilting import (
    REFERENCE_POSITION,
    TILT_POSITIONS,
    compute_tilt_loaded_reading,
    compute_tilt_unloaded_reading,
    compute_tilting_loaded_check,
    compute_tilting_unloaded_check,
    generate_tilting_mid_load,
)
from engine.types import AccuracyClass, VerificationType
from engine.weighing import compute_weighing_result

D = Decimal

_CLASS = AccuracyClass.III
_VTYPE = VerificationType.INITIAL
_E = D("1")


def test_tilt_positions_are_1_through_5_with_1_as_reference():
    assert TILT_POSITIONS == (1, 2, 3, 4, 5)
    assert REFERENCE_POSITION == 1


def test_generate_tilting_mid_load_is_half_of_max():
    assert generate_tilting_mid_load(max_capacity=D("1000")) == D("500")


def test_generate_tilting_mid_load_rejects_non_positive_max_capacity():
    with pytest.raises(ValueError):
        generate_tilting_mid_load(max_capacity=D("0"))


def test_unloaded_reading_delegates_to_compute_weighing_result_with_l_and_e0_zero():
    result = compute_tilt_unloaded_reading(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, I=D("100.4"), delta_l=D("0.5"))
    direct = compute_weighing_result(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("0"), I=D("100.4"), delta_l=D("0.5"), E0=D("0"))
    assert result == direct
    assert result.E == D("100.4")  # delta_l=e/2 cancels the +1/2e term -> E = I


def test_loaded_reading_uses_the_position_s_own_e0():
    e0 = D("100.4")  # this position's own unloaded E
    result = compute_tilt_loaded_reading(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("500"), I=D("500.6"), delta_l=D("0.5"), E0=e0)
    assert result.E == D("0.6")  # I - L (delta_l cancels)
    assert result.Ec == D("0.6") - e0


def test_unloaded_check_passes_when_all_positions_within_2e_of_reference():
    e0s = {1: D("100.0"), 2: D("100.1"), 3: D("100.2"), 4: D("99.9"), 5: D("101.5")}  # max dev from pos1 = 1.5
    result = compute_tilting_unloaded_check(e=_E, position_e0s=e0s)
    assert result.reference_e0 == D("100.0")
    assert result.limit == D("2")  # 2 * e
    assert result.max_abs_deviation == D("1.5")
    assert result.within_limit is True


def test_unloaded_check_at_the_2e_boundary_is_inclusive():
    e0s = {1: D("100.0"), 2: D("102.0")}  # deviation exactly 2e
    result = compute_tilting_unloaded_check(e=_E, position_e0s=e0s)
    assert result.max_abs_deviation == D("2")
    assert result.within_limit is True


def test_unloaded_check_just_over_2e_fails():
    e0s = {1: D("100.0"), 2: D("102.01")}
    result = compute_tilting_unloaded_check(e=_E, position_e0s=e0s)
    assert result.within_limit is False


def test_unloaded_check_requires_the_reference_position():
    with pytest.raises(ValueError):
        compute_tilting_unloaded_check(e=_E, position_e0s={2: D("100.0"), 3: D("100.1")})


def test_unloaded_check_rejects_empty_positions():
    with pytest.raises(ValueError):
        compute_tilting_unloaded_check(e=_E, position_e0s={})


def test_unloaded_check_can_run_with_a_partial_set_of_positions_so_far():
    # Only the reference + one tilted position submitted so far — a
    # legitimate in-progress state, not an error.
    result = compute_tilting_unloaded_check(e=_E, position_e0s={1: D("100.0"), 3: D("100.5")})
    assert result.max_abs_deviation == D("0.5")


# Mid load: L=500 -> m=500 -> Class III Band 1 (m<=500) -> mpe=0.5g.
def test_loaded_check_passes_when_all_positions_within_mpe_of_reference():
    ecs = {1: D("0.2"), 2: D("0.3"), 3: D("0.1"), 4: D("0.6"), 5: D("-0.1")}  # max dev from pos1 (0.2) = 0.4
    result = compute_tilting_loaded_check(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("500"), position_ecs=ecs)
    assert result.mpe == D("0.5")
    assert result.reference_ec == D("0.2")
    assert result.max_abs_deviation == D("0.4")
    assert result.within_mpe is True


def test_loaded_check_at_the_mpe_boundary_is_inclusive():
    ecs = {1: D("0.0"), 2: D("0.5")}  # deviation exactly mpe (0.5)
    result = compute_tilting_loaded_check(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("500"), position_ecs=ecs)
    assert result.max_abs_deviation == D("0.5")
    assert result.within_mpe is True


def test_loaded_check_just_over_mpe_fails():
    ecs = {1: D("0.0"), 2: D("0.51")}
    result = compute_tilting_loaded_check(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("500"), position_ecs=ecs)
    assert result.within_mpe is False


def test_loaded_check_requires_the_reference_position():
    with pytest.raises(ValueError):
        compute_tilting_loaded_check(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("500"), position_ecs={2: D("0.1")})


def test_two_loaded_rows_at_different_loads_get_different_mpe():
    # Mid load L=500 -> Band 1 -> mpe=0.5g; Max load L=1000 -> Band 2 (500 <
    # m <= 2000) -> mpe=1.0g — proving each loaded row's mpe is genuinely
    # its own, not shared.
    ecs = {1: D("0.1")}
    mid = compute_tilting_loaded_check(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("500"), position_ecs=ecs)
    max_row = compute_tilting_loaded_check(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("1000"), position_ecs=ecs)
    assert mid.mpe == D("0.5")
    assert max_row.mpe == D("1.0")


def test_loaded_check_rejects_wrong_type_accuracy_class():
    with pytest.raises(TypeError):
        compute_tilting_loaded_check(accuracy_class="III", verification_type=_VTYPE, e=_E, L=D("500"), position_ecs={1: D("0.1")})


def test_loaded_check_rejects_negative_load():
    with pytest.raises(ValueError):
        compute_tilting_loaded_check(accuracy_class=_CLASS, verification_type=_VTYPE, e=_E, L=D("-1"), position_ecs={1: D("0.1")})
