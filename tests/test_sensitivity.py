"""engine/sensitivity.py — the pass threshold is tiered by accuracy class
AND Max, not a single fixed number; these tests cover every tier and the
30 kg (30000 g) boundary on both sides.
"""

from decimal import Decimal

import pytest

from engine.sensitivity import MAX_THRESHOLD_GRAMS, compute_sensitivity, generate_sensitivity_checks, sensitivity_threshold_mm
from engine.types import AccuracyClass, VerificationType

D = Decimal

_VTYPE = VerificationType.INITIAL


def test_generate_sensitivity_checks_uses_min_capacity_as_low_anchor():
    checks = generate_sensitivity_checks(max_capacity=D("6000"), min_capacity=D("20"))
    assert checks == [D("20"), D("3000"), D("6000")]


def test_generate_sensitivity_checks_falls_back_without_min_capacity():
    checks = generate_sensitivity_checks(max_capacity=D("6000"), min_capacity=None)
    assert checks[0] == D("6000") * D("0.1")


def test_generate_sensitivity_checks_rejects_non_positive_max_capacity():
    with pytest.raises(ValueError):
        generate_sensitivity_checks(max_capacity=D("0"), min_capacity=None)


@pytest.mark.parametrize("accuracy_class", [AccuracyClass.I, AccuracyClass.II])
def test_threshold_is_1mm_for_class_1_and_2_regardless_of_max(accuracy_class):
    assert sensitivity_threshold_mm(accuracy_class=accuracy_class, max_capacity=D("1")) == D("1")
    assert sensitivity_threshold_mm(accuracy_class=accuracy_class, max_capacity=D("1000000")) == D("1")


@pytest.mark.parametrize("accuracy_class", [AccuracyClass.III, AccuracyClass.IIII])
def test_threshold_is_2mm_for_class_3_and_4_at_or_under_30kg(accuracy_class):
    assert sensitivity_threshold_mm(accuracy_class=accuracy_class, max_capacity=MAX_THRESHOLD_GRAMS) == D("2")
    assert sensitivity_threshold_mm(accuracy_class=accuracy_class, max_capacity=D("1")) == D("2")


@pytest.mark.parametrize("accuracy_class", [AccuracyClass.III, AccuracyClass.IIII])
def test_threshold_is_5mm_for_class_3_and_4_over_30kg(accuracy_class):
    assert sensitivity_threshold_mm(accuracy_class=accuracy_class, max_capacity=MAX_THRESHOLD_GRAMS + D("1")) == D("5")


def test_30kg_boundary_is_exactly_at_30000_grams():
    assert MAX_THRESHOLD_GRAMS == D("30000")


def test_threshold_rejects_non_positive_max_capacity():
    with pytest.raises(ValueError):
        sensitivity_threshold_mm(accuracy_class=AccuracyClass.III, max_capacity=D("0"))


def test_threshold_rejects_wrong_type_accuracy_class():
    with pytest.raises(TypeError):
        sensitivity_threshold_mm(accuracy_class="III", max_capacity=D("1000"))


_L = D("500")  # e=1g, Class III -> m=500 -> Band 1 -> mpe=0.5g


def test_compute_sensitivity_extra_load_is_abs_mpe():
    result = compute_sensitivity(
        accuracy_class=AccuracyClass.III, verification_type=_VTYPE, e=D("1"), max_capacity=D("1000"),
        L=_L, permanent_displacement_mm=D("2"),
    )
    assert result.mpe == D("0.5")
    assert result.extra_load == D("0.5")


def test_compute_sensitivity_passes_at_the_threshold_boundary_inclusive():
    # Class III, Max=1000g (<=30000) -> threshold=2mm.
    result = compute_sensitivity(
        accuracy_class=AccuracyClass.III, verification_type=_VTYPE, e=D("1"), max_capacity=D("1000"),
        L=_L, permanent_displacement_mm=D("2"),
    )
    assert result.threshold_mm == D("2")
    assert result.passed is True


def test_compute_sensitivity_fails_just_under_threshold():
    result = compute_sensitivity(
        accuracy_class=AccuracyClass.III, verification_type=_VTYPE, e=D("1"), max_capacity=D("1000"),
        L=_L, permanent_displacement_mm=D("1.9"),
    )
    assert result.passed is False


def test_compute_sensitivity_uses_the_5mm_tier_over_30kg():
    result = compute_sensitivity(
        accuracy_class=AccuracyClass.III, verification_type=_VTYPE, e=D("1"), max_capacity=MAX_THRESHOLD_GRAMS + D("1000"),
        L=_L, permanent_displacement_mm=D("4.9"),
    )
    assert result.threshold_mm == D("5")
    assert result.passed is False


def test_compute_sensitivity_requires_every_argument():
    kwargs = dict(
        accuracy_class=AccuracyClass.III, verification_type=_VTYPE, e=D("1"), max_capacity=D("1000"),
        L=_L, permanent_displacement_mm=D("2"),
    )
    for missing in kwargs:
        bad = {k: v for k, v in kwargs.items() if k != missing}
        with pytest.raises(TypeError):
            compute_sensitivity(**bad)


def test_compute_sensitivity_rejects_negative_displacement():
    with pytest.raises(ValueError):
        compute_sensitivity(
            accuracy_class=AccuracyClass.III, verification_type=_VTYPE, e=D("1"), max_capacity=D("1000"),
            L=_L, permanent_displacement_mm=D("-1"),
        )
