"""engine/comparison.py — the shared cross-run comparison math (durability/
variation error) behind Weighing's multi-run support (clause 1) and, later,
Damp heat (clause 13) and Endurance (clause 15). Boundary cases (variation
error exactly at mpe, from both sides) and sign handling (the order of the
two runs, and the sign of each Ec, must never change the verdict) are the
two things this function's own correctness hinges on — proven here, not
just exercised once.
"""

from decimal import Decimal

import pytest

from engine.comparison import compute_durability_check, compute_run_comparison

D = Decimal


def test_identical_runs_have_zero_variation_error():
    result = compute_run_comparison(Ec_a=D("0.3"), Ec_b=D("0.3"), mpe=D("0.5"))
    assert result.variation_error == D("0")
    assert result.passed is True
    assert result.margin == D("0.5")


def test_variation_error_is_a_magnitude_order_does_not_matter():
    forward = compute_run_comparison(Ec_a=D("0.7"), Ec_b=D("0.3"), mpe=D("0.5"))
    backward = compute_run_comparison(Ec_a=D("0.3"), Ec_b=D("0.7"), mpe=D("0.5"))
    assert forward.variation_error == backward.variation_error == D("0.4")
    assert forward.passed == backward.passed == True


def test_opposite_signed_ec_values_compute_the_correct_magnitude():
    # Ec_a=+0.3, Ec_b=-0.3 -> the drift between them is 0.6, not 0.
    result = compute_run_comparison(Ec_a=D("0.3"), Ec_b=D("-0.3"), mpe=D("0.5"))
    assert result.variation_error == D("0.6")
    assert result.passed is False


def test_both_negative_ec_values():
    result = compute_run_comparison(Ec_a=D("-0.2"), Ec_b=D("-0.5"), mpe=D("0.5"))
    assert result.variation_error == D("0.3")
    assert result.passed is True


def test_variation_error_exactly_at_mpe_passes_limit_inclusive():
    result = compute_run_comparison(Ec_a=D("0.9"), Ec_b=D("0.4"), mpe=D("0.5"))
    assert result.variation_error == D("0.5")
    assert result.passed is True
    assert result.margin == D("0")


def test_variation_error_just_over_mpe_fails():
    result = compute_run_comparison(Ec_a=D("0.901"), Ec_b=D("0.4"), mpe=D("0.5"))
    assert result.variation_error == D("0.501")
    assert result.passed is False
    assert result.margin < 0


def test_variation_error_just_under_mpe_passes():
    result = compute_run_comparison(Ec_a=D("0.899"), Ec_b=D("0.4"), mpe=D("0.5"))
    assert result.variation_error == D("0.499")
    assert result.passed is True
    assert result.margin > 0


def test_zero_mpe_requires_exact_agreement():
    exact = compute_run_comparison(Ec_a=D("0.4"), Ec_b=D("0.4"), mpe=D("0"))
    assert exact.passed is True
    off = compute_run_comparison(Ec_a=D("0.4"), Ec_b=D("0.401"), mpe=D("0"))
    assert off.passed is False


def test_rejects_negative_mpe():
    with pytest.raises(ValueError):
        compute_run_comparison(Ec_a=D("0"), Ec_b=D("0"), mpe=D("-1"))


@pytest.mark.parametrize("bad_field", ["Ec_a", "Ec_b", "mpe"])
def test_rejects_non_decimal_inputs(bad_field):
    kwargs = {"Ec_a": D("0"), "Ec_b": D("0"), "mpe": D("0.5")}
    kwargs[bad_field] = float(kwargs[bad_field])
    with pytest.raises(TypeError):
        compute_run_comparison(**kwargs)


def test_requires_every_argument():
    with pytest.raises(TypeError):
        compute_run_comparison(Ec_a=D("0"), Ec_b=D("0"))


# -- compute_durability_check (Endurance's own aggregate verdict) ----------


def _comparison(ec_a, ec_b, mpe):
    return compute_run_comparison(Ec_a=D(ec_a), Ec_b=D(ec_b), mpe=D(mpe))


def test_durability_check_passes_when_every_load_is_within_mpe():
    comparisons = [_comparison("0.1", "0.1", "0.5"), _comparison("0.2", "0.3", "0.5")]
    result = compute_durability_check(comparisons)
    assert result.all_passed is True
    assert result.comparisons == tuple(comparisons)


def test_durability_check_fails_if_even_one_load_exceeds_mpe():
    comparisons = [_comparison("0.1", "0.1", "0.5"), _comparison("0.9", "0.1", "0.5")]  # 0.8 > 0.5
    result = compute_durability_check(comparisons)
    assert result.all_passed is False


def test_durability_check_single_passing_entry_passes():
    result = compute_durability_check([_comparison("0.3", "0.3", "0.5")])
    assert result.all_passed is True


def test_durability_check_boundary_variation_error_exactly_at_mpe_passes():
    result = compute_durability_check([_comparison("0.9", "0.4", "0.5")])  # variation_error == mpe
    assert result.all_passed is True


def test_durability_check_empty_comparisons_never_counts_as_a_pass():
    result = compute_durability_check([])
    assert result.all_passed is False
    assert result.comparisons == ()


def test_durability_check_rejects_non_comparison_elements():
    with pytest.raises(TypeError):
        compute_durability_check([_comparison("0", "0", "0.5"), "not-a-comparison"])


def test_durability_check_preserves_input_order_and_is_a_tuple():
    comparisons = [_comparison("0.1", "0.1", "0.5"), _comparison("0.2", "0.2", "0.5")]
    result = compute_durability_check(comparisons)
    assert isinstance(result.comparisons, tuple)
    assert list(result.comparisons) == comparisons
