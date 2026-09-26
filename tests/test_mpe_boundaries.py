"""The real acceptance criterion (CLAUDE.md): no calculated verdict is trusted
until this boundary-value table passes. Covers every MPE band edge from both
sides for all four classes, the at-limit-inclusive/just-over verdict boundary,
symmetric negative errors, in_service doubling, and Max/Min-of-table loads.
"""

from decimal import Decimal

import pytest

from engine.mpe import lookup_mpe
from engine.types import AccuracyClass, VerificationType
from engine.weighing import compute_weighing_result

D = Decimal


# ---------------------------------------------------------------------------
# Table 6 band edges, both sides, all four classes (initial verification).
# (accuracy_class, m, expected_mpe_in_e)
# ---------------------------------------------------------------------------
BAND_EDGE_CASES = [
    # Class I: 0.5e for 0<=m<=50000, 1.0e for 50000<m<=200000, 1.5e for m>200000.
    (AccuracyClass.I, D("0"), D("0.5")),
    (AccuracyClass.I, D("50000"), D("0.5")),
    (AccuracyClass.I, D("50001"), D("1.0")),
    (AccuracyClass.I, D("200000"), D("1.0")),
    (AccuracyClass.I, D("200001"), D("1.5")),
    (AccuracyClass.I, D("500000"), D("1.5")),  # unbounded top band, far above the last edge
    # Class II: 0.5e for 0<=m<=5000, 1.0e for 5000<m<=20000, 1.5e for 20000<m<=100000.
    (AccuracyClass.II, D("0"), D("0.5")),
    (AccuracyClass.II, D("5000"), D("0.5")),
    (AccuracyClass.II, D("5001"), D("1.0")),
    (AccuracyClass.II, D("20000"), D("1.0")),
    (AccuracyClass.II, D("20001"), D("1.5")),
    (AccuracyClass.II, D("100000"), D("1.5")),  # Max of the table
    # Class III: 0.5e for 0<=m<=500, 1.0e for 500<m<=2000, 1.5e for 2000<m<=10000.
    (AccuracyClass.III, D("0"), D("0.5")),  # Min (near-zero load)
    (AccuracyClass.III, D("500"), D("0.5")),
    (AccuracyClass.III, D("501"), D("1.0")),
    (AccuracyClass.III, D("2000"), D("1.0")),
    (AccuracyClass.III, D("2001"), D("1.5")),
    (AccuracyClass.III, D("10000"), D("1.5")),  # Max of the table
    # Class IIII: 0.5e for 0<=m<=50, 1.0e for 50<m<=200, 1.5e for 200<m<=1000.
    (AccuracyClass.IIII, D("0"), D("0.5")),
    (AccuracyClass.IIII, D("50"), D("0.5")),
    (AccuracyClass.IIII, D("51"), D("1.0")),
    (AccuracyClass.IIII, D("200"), D("1.0")),
    (AccuracyClass.IIII, D("201"), D("1.5")),
    (AccuracyClass.IIII, D("1000"), D("1.5")),  # Max of the table
]


@pytest.mark.parametrize("accuracy_class, m, expected_mpe_in_e", BAND_EDGE_CASES)
def test_mpe_band_edges_initial(accuracy_class, m, expected_mpe_in_e):
    result = lookup_mpe(
        accuracy_class=accuracy_class,
        m=m,
        e=D("1"),
        verification_type=VerificationType.INITIAL,
    )
    assert result.mpe_in_e == expected_mpe_in_e
    assert result.mpe_grams == expected_mpe_in_e  # e=1, so mpe_in_e == mpe_grams here


@pytest.mark.parametrize("accuracy_class, m, expected_mpe_in_e", BAND_EDGE_CASES)
def test_mpe_band_edges_subsequent_same_as_initial(accuracy_class, m, expected_mpe_in_e):
    # "initial and subsequent use these values" — subsequent must match initial exactly.
    result = lookup_mpe(
        accuracy_class=accuracy_class,
        m=m,
        e=D("1"),
        verification_type=VerificationType.SUBSEQUENT,
    )
    assert result.mpe_in_e == expected_mpe_in_e


@pytest.mark.parametrize(
    "accuracy_class, m",
    [
        (AccuracyClass.II, D("100001")),
        (AccuracyClass.III, D("10001")),
        (AccuracyClass.IIII, D("1001")),
    ],
)
def test_mpe_raises_above_top_of_table_for_bounded_classes(accuracy_class, m):
    # Classes II/III/IIII have an explicit, bounded top row — going past it is
    # outside the defined table, so this must raise rather than guess.
    with pytest.raises(ValueError):
        lookup_mpe(
            accuracy_class=accuracy_class,
            m=m,
            e=D("1"),
            verification_type=VerificationType.INITIAL,
        )


# ---------------------------------------------------------------------------
# in_service doubling: same m, same class, doubled mpe.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("accuracy_class, m, expected_mpe_in_e", BAND_EDGE_CASES)
def test_mpe_in_service_doubles_initial(accuracy_class, m, expected_mpe_in_e):
    initial = lookup_mpe(
        accuracy_class=accuracy_class,
        m=m,
        e=D("1"),
        verification_type=VerificationType.INITIAL,
    )
    in_service = lookup_mpe(
        accuracy_class=accuracy_class,
        m=m,
        e=D("1"),
        verification_type=VerificationType.IN_SERVICE,
    )
    assert in_service.mpe_in_e == initial.mpe_in_e * D("2")
    assert in_service.mpe_grams == initial.mpe_grams * D("2")


def test_in_service_doubling_flips_the_verdict():
    # Class III, m=300 (Band 1): mpe_initial=0.5g, mpe_in_service=1.0g.
    # Ec=0.6g fails against 0.5g but passes against 1.0g — same load, same
    # reading, different verdict purely from the verification-type doubling.
    e = D("1")
    L = D("300")
    delta_l = e / 2  # cancels the +1/2e term, isolating E = I - L
    E0 = D("0")
    I = D("300.6")

    initial = compute_weighing_result(
        accuracy_class=AccuracyClass.III,
        verification_type=VerificationType.INITIAL,
        e=e,
        L=L,
        I=I,
        delta_l=delta_l,
        E0=E0,
    )
    in_service = compute_weighing_result(
        accuracy_class=AccuracyClass.III,
        verification_type=VerificationType.IN_SERVICE,
        e=e,
        L=L,
        I=I,
        delta_l=delta_l,
        E0=E0,
    )

    assert initial.mpe == D("0.5")
    assert initial.passed is False
    assert in_service.mpe == D("1.0")
    assert in_service.passed is True


# ---------------------------------------------------------------------------
# Verdict boundary: exactly at the MPE limit is a PASS (inclusive); just over
# is a FAIL. Checked in both directions (positive and negative Ec).
# ---------------------------------------------------------------------------
def _result_with_ec(target_ec: Decimal, E0: Decimal = D("0")) -> "WeighingResult":  # noqa: F821
    # Class III, m=300 -> mpe=0.5g. delta_l=e/2 cancels the +1/2e term, so
    # E = I - L, and Ec = E - E0. Choosing I = L + E0 + target_ec gives exact
    # control over Ec for boundary testing.
    e = D("1")
    L = D("300")
    delta_l = e / 2
    I = L + E0 + target_ec
    return compute_weighing_result(
        accuracy_class=AccuracyClass.III,
        verification_type=VerificationType.INITIAL,
        e=e,
        L=L,
        I=I,
        delta_l=delta_l,
        E0=E0,
    )


@pytest.mark.parametrize(
    "target_ec, expected_passed",
    [
        (D("0.5"), True),  # exactly at the limit, positive side -> inclusive PASS
        (D("0.51"), False),  # just over, positive side -> FAIL
        (D("-0.5"), True),  # exactly at the limit, negative side -> inclusive PASS
        (D("-0.51"), False),  # just over, negative side -> FAIL
        (D("0"), True),  # zero error, trivially within tolerance
    ],
)
def test_verdict_at_and_just_past_the_mpe_limit(target_ec, expected_passed):
    result = _result_with_ec(target_ec)
    assert result.Ec == target_ec
    assert result.passed is expected_passed
    assert (result.margin >= 0) is expected_passed


def test_verdict_respects_nonzero_e0_offset():
    # E0 != 0 must shift the effective error (Ec = E - E0), not just get ignored.
    result = _result_with_ec(D("0.5"), E0=D("0.2"))
    assert result.E0 == D("0.2")
    assert result.Ec == D("0.5")
    assert result.passed is True
