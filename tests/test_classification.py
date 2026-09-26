"""Tests for engine.classification (OIML R76-1 Table 3 accuracy-class
derivation) — no DB, no HTTP, pure."""

from decimal import Decimal

import pytest

from engine.classification import classify_instrument
from engine.types import AccuracyClass

D = Decimal


# ---------------------------------------------------------------------------
# One clean valid case per class.
# ---------------------------------------------------------------------------
def test_class_i_valid_case():
    # e=0.01g, Max=2000g -> n=200000: >=50000 (Class I's minimum) AND above
    # Class II's n_max of 100000, so this is unambiguously Class I only.
    # Min=1g (>=100e=1g).
    result = classify_instrument(e=D("0.01"), max_capacity=D("2000"), min_capacity=D("1"))
    assert result.qualified_classes == (AccuracyClass.I,)
    assert result.is_valid
    assert result.n == D("200000")
    assert result.reason is None


def test_class_ii_low_e_row_valid_case():
    # e=0.01g (in [0.001,0.05]), Max=500g -> n=50000 (in [100,100000]); Min>=20e=0.2g
    result = classify_instrument(e=D("0.01"), max_capacity=D("500"), min_capacity=D("0.2"))
    assert AccuracyClass.II in result.qualified_classes


def test_class_ii_high_e_row_valid_case():
    # e=0.2g (>=0.1), Max=10000g -> n=50000 (in [5000,100000]); Min>=50e=10g
    result = classify_instrument(e=D("0.2"), max_capacity=D("10000"), min_capacity=D("10"))
    assert AccuracyClass.II in result.qualified_classes


def test_class_iii_low_e_row_valid_case():
    # e=1g (in [0.1,2]), Max=6000g -> n=6000 (in [100,10000]); Min>=20e=20g
    result = classify_instrument(e=D("1"), max_capacity=D("6000"), min_capacity=D("20"))
    assert result.qualified_classes == (AccuracyClass.III,)
    assert result.n == D("6000")


def test_class_iii_high_e_row_valid_case():
    # e=5g (>=5), Max=40000g -> n=8000 (in [500,10000]); Min>=20e=100g
    result = classify_instrument(e=D("5"), max_capacity=D("40000"), min_capacity=D("100"))
    assert result.qualified_classes == (AccuracyClass.III,)


def test_class_iiii_valid_case():
    # e=5g (>=5), Max=3000g -> n=600 (in [100,1000]); Min>=10e=50g
    result = classify_instrument(e=D("5"), max_capacity=D("3000"), min_capacity=D("50"))
    assert result.qualified_classes == (AccuracyClass.IIII,)


# ---------------------------------------------------------------------------
# Boundary cases: n exactly at a class's min/max n.
# ---------------------------------------------------------------------------
def test_class_iii_low_e_row_n_at_exact_minimum():
    # n_min=100 for Class III's low-e row.
    result = classify_instrument(e=D("1"), max_capacity=D("100"), min_capacity=D("20"))
    assert result.n == D("100")
    assert AccuracyClass.III in result.qualified_classes


def test_class_iii_low_e_row_n_at_exact_maximum():
    # n_max=10000 for Class III's low-e row (and Table 3's own n_max for III overall).
    result = classify_instrument(e=D("1"), max_capacity=D("10000"), min_capacity=D("20"))
    assert result.n == D("10000")
    assert AccuracyClass.III in result.qualified_classes


def test_n_one_below_class_iii_minimum_fails_it():
    result = classify_instrument(e=D("1"), max_capacity=D("99"), min_capacity=D("20"))
    assert AccuracyClass.III not in result.qualified_classes


def test_class_i_n_at_exact_minimum_qualifies():
    result = classify_instrument(e=D("0.01"), max_capacity=D("500"), min_capacity=D("1"))
    assert result.n == D("50000")
    assert AccuracyClass.I in result.qualified_classes


def test_class_i_n_one_below_minimum_fails():
    result = classify_instrument(e=D("0.01"), max_capacity=D("499.99"), min_capacity=D("1"))
    assert result.n == D("49999")
    assert AccuracyClass.I not in result.qualified_classes


# ---------------------------------------------------------------------------
# The actual bug this task fixes: under the OLD model, a client could force
# accuracy_class="III" with e=1g, Max=15000g (n=15000) — n=15000 exceeds
# Class III's own n_max of 10000 (Table 3, and engine.mpe.BAND_TABLE's top
# band edge for III), which later crashed the Weighing load-sequence
# endpoint (engine.mpe.lookup_mpe has no band for m>10000 under class III).
# Under the NEW derive-don't-choose model, classify_instrument never offers
# Class III for these parameters at all — it correctly resolves to Class II
# instead (n=15000 fits Class II's high-e row, n in [5000,100000]) when Min
# is adequate for Class II, and cleanly REJECTS (not silently accepts as
# III) when Min is too low for every class the e/n combination could fit.
# ---------------------------------------------------------------------------
def test_bug_scenario_n_15000_never_qualifies_for_class_iii():
    result = classify_instrument(e=D("1"), max_capacity=D("15000"), min_capacity=D("50"))
    assert AccuracyClass.III not in result.qualified_classes


def test_bug_scenario_n_15000_resolves_to_class_ii_when_min_adequate():
    # Min=50 satisfies Class II's high-e-row requirement (Min>=50e=50g).
    result = classify_instrument(e=D("1"), max_capacity=D("15000"), min_capacity=D("50"))
    assert result.qualified_classes == (AccuracyClass.II,)
    assert result.is_valid


def test_bug_scenario_n_15000_rejected_with_reason_when_min_too_low_everywhere():
    # Min=10 is too low for Class I (needs 100e=100g) and Class II's
    # applicable row (needs 50e=50g); n=15000 also exceeds Class III's
    # n_max, so nothing qualifies — must be a clean rejection, not a
    # silent fallback to an invalid class.
    result = classify_instrument(e=D("1"), max_capacity=D("15000"), min_capacity=D("10"))
    assert result.qualified_classes == ()
    assert not result.is_valid
    assert result.n == D("15000")
    assert "n=15000" in result.reason
    assert "10000" in result.reason  # Class III's n_max named in the reason
    assert "Class III" in result.reason


# ---------------------------------------------------------------------------
# Min-too-low cases (n otherwise fine).
# ---------------------------------------------------------------------------
def test_min_too_low_for_class_iii_rejected_with_reason():
    # n=5000 fits Class III's low-e row range fine, but Min=1g < 20e=20g.
    result = classify_instrument(e=D("1"), max_capacity=D("5000"), min_capacity=D("1"))
    assert AccuracyClass.III not in result.qualified_classes


def test_min_exactly_at_required_multiple_qualifies():
    result = classify_instrument(e=D("1"), max_capacity=D("5000"), min_capacity=D("20"))
    assert AccuracyClass.III in result.qualified_classes


def test_min_one_below_required_multiple_fails():
    result = classify_instrument(e=D("1"), max_capacity=D("5000"), min_capacity=D("19.999"))
    assert AccuracyClass.III not in result.qualified_classes


# ---------------------------------------------------------------------------
# A case matching multiple classes.
# ---------------------------------------------------------------------------
def test_multiple_classes_qualify_when_n_and_min_both_satisfy_more_than_one():
    # e=1g, n=8000 (Class III's low-e row: [100,10000]); Min=50g satisfies
    # BOTH Class III's 20e=20g requirement AND Class II's high-e-row
    # 50e=50g requirement, and n=8000 also fits Class II's [5000,100000].
    result = classify_instrument(e=D("1"), max_capacity=D("8000"), min_capacity=D("50"))
    assert set(result.qualified_classes) == {AccuracyClass.II, AccuracyClass.III}
    assert result.is_valid
    # Most-precise-first ordering (I < II < III < IIII in precision).
    assert result.qualified_classes.index(AccuracyClass.II) < result.qualified_classes.index(AccuracyClass.III)


# ---------------------------------------------------------------------------
# e-format validation (clause 3.4.2: e = 1/2/5 x 10^k).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("e", ["1", "2", "5", "10", "20", "50", "0.1", "0.2", "0.5", "0.001", "100"])
def test_valid_e_values_pass_the_format_check(e):
    result = classify_instrument(e=D(e), max_capacity=D(e) * 100000, min_capacity=D(e) * 1000)
    # Doesn't assert a specific class — just that the e-format rejection
    # never fires for a genuinely valid 1/2/5 x 10^k value.
    assert result.reason is None or "verification scale interval" not in (result.reason or "")


@pytest.mark.parametrize("e", ["3", "15", "0.06", "7", "1.5", "4"])
def test_invalid_e_values_rejected_with_reason(e):
    result = classify_instrument(e=D(e), max_capacity=D("1000"), min_capacity=D("10"))
    assert result.qualified_classes == ()
    assert "verification scale interval" in result.reason
    assert e in result.reason or str(D(e)) in result.reason


def test_e_zero_or_negative_raises_value_error_not_a_rejection_result():
    # A structurally impossible value is a caller bug, not a legitimate
    # "doesn't fit any class" business outcome — raises immediately, same
    # convention as engine.weighing/engine.load_sequence.
    with pytest.raises(ValueError):
        classify_instrument(e=D("0"), max_capacity=D("1000"), min_capacity=D("10"))
    with pytest.raises(ValueError):
        classify_instrument(e=D("-1"), max_capacity=D("1000"), min_capacity=D("10"))


# ---------------------------------------------------------------------------
# clause 3.4.2: d < e <= 10d, when d is given.
# ---------------------------------------------------------------------------
def test_d_within_valid_ratio_of_e_does_not_block_classification():
    result = classify_instrument(e=D("1"), max_capacity=D("6000"), min_capacity=D("20"), d=D("0.5"))
    assert result.is_valid


def test_d_equal_to_e_is_rejected_strict_inequality():
    # Spec is d < e (strict), not d <= e.
    result = classify_instrument(e=D("1"), max_capacity=D("6000"), min_capacity=D("20"), d=D("1"))
    assert result.qualified_classes == ()
    assert "d < e" in result.reason


def test_d_more_than_ten_times_smaller_than_e_is_rejected():
    result = classify_instrument(e=D("1"), max_capacity=D("6000"), min_capacity=D("20"), d=D("0.05"))
    assert result.qualified_classes == ()
    assert "d < e" in result.reason


def test_d_none_skips_the_check_entirely():
    result = classify_instrument(e=D("1"), max_capacity=D("6000"), min_capacity=D("20"), d=None)
    assert result.is_valid


# ---------------------------------------------------------------------------
# No silent defaults / bad types.
# ---------------------------------------------------------------------------
def test_requires_every_argument_except_d():
    with pytest.raises(TypeError):
        classify_instrument(max_capacity=D("1000"), min_capacity=D("10"))
    with pytest.raises(TypeError):
        classify_instrument(e=D("1"), min_capacity=D("10"))
    with pytest.raises(TypeError):
        classify_instrument(e=D("1"), max_capacity=D("1000"))
    # min_capacity is NOT optional here (unlike load_sequence's), since every
    # Table 3 row needs it — omitting it is a TypeError, not a None default.
    classify_instrument(e=D("1"), max_capacity=D("1000"), min_capacity=D("10"))  # doesn't raise


def test_rejects_float_instead_of_decimal():
    with pytest.raises(TypeError):
        classify_instrument(e=1.0, max_capacity=D("1000"), min_capacity=D("10"))
    with pytest.raises(TypeError):
        classify_instrument(e=D("1"), max_capacity=1000.0, min_capacity=D("10"))
    with pytest.raises(TypeError):
        classify_instrument(e=D("1"), max_capacity=D("1000"), min_capacity=10.0)
    with pytest.raises(TypeError):
        classify_instrument(e=D("1"), max_capacity=D("1000"), min_capacity=D("10"), d=0.5)


def test_negative_min_capacity_raises_value_error():
    with pytest.raises(ValueError):
        classify_instrument(e=D("1"), max_capacity=D("1000"), min_capacity=D("-1"))
