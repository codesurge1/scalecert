"""engine/repeatability.py — structurally different from Weighing: two fixed
loads (not a load sequence), no E0 correction, and two independent
per-series pass criteria (every reading within mpe, AND the series' spread
within mpe). These tests cover the load generator, the two-criteria logic
(each criterion failing independently, and both at their inclusive
boundary), that E is signed (not abs) for the spread calculation, that each
series gets its own mpe, and the same no-silent-defaults input validation
the rest of the engine has.
"""

from decimal import Decimal

import pytest

from engine.repeatability import compute_repeatability_series, generate_repeatability_load
from engine.types import AccuracyClass, VerificationType

D = Decimal

_CLASS = AccuracyClass.III
_VTYPE = VerificationType.INITIAL
_E = D("1")


def test_generate_repeatability_load_series_1_is_half_of_max():
    assert generate_repeatability_load(series_no=1, max_capacity=D("1000")) == D("500")


def test_generate_repeatability_load_series_2_is_max_itself():
    assert generate_repeatability_load(series_no=2, max_capacity=D("1000")) == D("1000")


def test_generate_repeatability_load_rejects_bad_series_no():
    with pytest.raises(ValueError):
        generate_repeatability_load(series_no=3, max_capacity=D("1000"))


def test_generate_repeatability_load_rejects_non_decimal_max_capacity():
    with pytest.raises(TypeError):
        generate_repeatability_load(series_no=1, max_capacity=1000.0)


def test_generate_repeatability_load_rejects_non_positive_max_capacity():
    with pytest.raises(ValueError):
        generate_repeatability_load(series_no=1, max_capacity=D("0"))


# Max=1000g, e=1g, Class III -> series 1 (L=500, m=500) lands exactly on the
# Band-1/Band-2 edge (upper bound inclusive) -> mpe=0.5g; series 2 (L=1000,
# m=1000) lands in Band 2 -> mpe=1.0g. Deliberately chosen so the two series
# have DIFFERENT mpe, proving "each series has its own mpe" for real, not
# coincidentally the same number.
_MAX_CAPACITY = D("1000")


def _series_1_kwargs(readings):
    return dict(
        accuracy_class=_CLASS,
        verification_type=_VTYPE,
        e=_E,
        series_no=1,
        L=generate_repeatability_load(series_no=1, max_capacity=_MAX_CAPACITY),
        readings=readings,
    )


def _series_2_kwargs(readings):
    return dict(
        accuracy_class=_CLASS,
        verification_type=_VTYPE,
        e=_E,
        series_no=2,
        L=generate_repeatability_load(series_no=2, max_capacity=_MAX_CAPACITY),
        readings=readings,
    )


def test_series_1_and_series_2_have_different_mpe_for_the_same_instrument():
    result_1 = compute_repeatability_series(**_series_1_kwargs([(D("500.1"), D("0"))]))
    result_2 = compute_repeatability_series(**_series_2_kwargs([(D("1000.2"), D("0"))]))
    assert result_1.mpe == D("0.5")
    assert result_2.mpe == D("1.0")


def test_no_e0_correction_e_equals_i_plus_half_e_minus_deltal_minus_l():
    # delta_l = e/2 makes the "+1/2*e - delta_l" term cancel, same trick
    # tests/test_worked_example.py uses, so E = I - L exactly, with no Ec/E0
    # anywhere in the result.
    result = compute_repeatability_series(**_series_1_kwargs([(D("500.3"), D("0.5"))]))
    assert result.readings[0].E == D("0.3")
    assert not hasattr(result.readings[0], "Ec")
    assert not hasattr(result.readings[0], "E0")


def test_passes_when_all_readings_within_mpe_and_spread_within_mpe():
    readings = [(D("500.1"), D("0.5")), (D("500.2"), D("0.5")), (D("500.3"), D("0.5"))]
    result = compute_repeatability_series(**_series_1_kwargs(readings))
    assert [r.E for r in result.readings] == [D("0.1"), D("0.2"), D("0.3")]
    assert result.e_max == D("0.3")
    assert result.e_min == D("0.1")
    assert result.spread == D("0.2")
    assert result.all_within_mpe is True
    assert result.spread_within_mpe is True
    assert result.passed is True


def test_fails_when_an_individual_reading_exceeds_mpe_even_if_spread_is_fine():
    # mpe=0.5g; both readings individually exceed it (E=0.6), but spread=0 —
    # criterion (a) alone must fail the series.
    readings = [(D("500.6"), D("0.5")), (D("500.6"), D("0.5"))]
    result = compute_repeatability_series(**_series_1_kwargs(readings))
    assert result.all_within_mpe is False
    assert result.spread_within_mpe is True
    assert result.passed is False


def test_fails_when_spread_exceeds_mpe_even_if_every_reading_is_individually_within_it():
    # mpe=0.5g; E=-0.3 and E=+0.3 are each individually within 0.5g, but the
    # spread (0.3 - (-0.3) = 0.6) exceeds it — criterion (b) alone must fail
    # the series. This also proves E is SIGNED for the spread, not abs(E):
    # abs(-0.3) and abs(0.3) would both be 0.3, never producing a spread
    # this large.
    readings = [(D("499.7"), D("0.5")), (D("500.3"), D("0.5"))]
    result = compute_repeatability_series(**_series_1_kwargs(readings))
    assert result.e_min == D("-0.3")
    assert result.e_max == D("0.3")
    assert result.spread == D("0.6")
    assert result.all_within_mpe is True
    assert result.spread_within_mpe is False
    assert result.passed is False


def test_individual_reading_at_mpe_boundary_is_within_mpe_inclusive():
    readings = [(D("500.5"), D("0.5"))]  # E = 0.5, mpe = 0.5 exactly
    result = compute_repeatability_series(**_series_1_kwargs(readings))
    assert result.readings[0].within_mpe is True
    assert result.all_within_mpe is True


def test_individual_reading_just_over_mpe_boundary_fails():
    readings = [(D("500.51"), D("0.5"))]  # E = 0.51 > mpe = 0.5
    result = compute_repeatability_series(**_series_1_kwargs(readings))
    assert result.readings[0].within_mpe is False


def test_spread_at_mpe_boundary_is_within_mpe_inclusive():
    # E values 0.0 and 0.5 -> spread = 0.5 == mpe exactly.
    readings = [(D("500.0"), D("0.5")), (D("500.5"), D("0.5"))]
    result = compute_repeatability_series(**_series_1_kwargs(readings))
    assert result.spread == D("0.5")
    assert result.spread_within_mpe is True
    assert result.passed is True


def test_spread_just_over_mpe_boundary_fails():
    readings = [(D("500.0"), D("0.5")), (D("500.51"), D("0.5"))]
    result = compute_repeatability_series(**_series_1_kwargs(readings))
    assert result.spread == D("0.51")
    assert result.spread_within_mpe is False
    assert result.passed is False


@pytest.mark.parametrize("missing", ["accuracy_class", "verification_type", "e", "series_no", "L", "readings"])
def test_compute_repeatability_series_requires_every_argument(missing):
    kwargs = _series_1_kwargs([(D("500.1"), D("0"))])
    del kwargs[missing]
    with pytest.raises(TypeError):
        compute_repeatability_series(**kwargs)


def test_compute_repeatability_series_rejects_wrong_type_enum_fields():
    kwargs = _series_1_kwargs([(D("500.1"), D("0"))])
    kwargs["accuracy_class"] = "III"
    with pytest.raises(TypeError):
        compute_repeatability_series(**kwargs)


def test_compute_repeatability_series_rejects_bad_series_no():
    kwargs = _series_1_kwargs([(D("500.1"), D("0"))])
    kwargs["series_no"] = 3
    with pytest.raises(ValueError):
        compute_repeatability_series(**kwargs)


def test_compute_repeatability_series_rejects_negative_load():
    kwargs = _series_1_kwargs([(D("500.1"), D("0"))])
    kwargs["L"] = D("-1")
    with pytest.raises(ValueError):
        compute_repeatability_series(**kwargs)


def test_compute_repeatability_series_rejects_empty_readings():
    kwargs = _series_1_kwargs([])
    with pytest.raises(ValueError):
        compute_repeatability_series(**kwargs)


def test_compute_repeatability_series_rejects_float_reading_values():
    kwargs = _series_1_kwargs([(500.1, D("0"))])  # I is a float, not Decimal
    with pytest.raises(TypeError):
        compute_repeatability_series(**kwargs)
