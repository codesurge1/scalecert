"""Tests for the deterministic Weighing load-sequence generator
(engine/load_sequence.py)."""

from decimal import Decimal

import pytest

from engine.load_sequence import MIN_VERIFICATION_LOAD_COUNT, generate_load_sequence
from engine.types import AccuracyClass, LoadKind, VerificationType

D = Decimal


def _by_kind(sequence, kind):
    return [entry for entry in sequence if entry.kind is kind]


# ---------------------------------------------------------------------------
# Class III, e=1g, Max/Min chosen so both band transitions (500e, 2000e) are
# in range, and Min qualifies (>=100mg).
# ---------------------------------------------------------------------------
def test_class_iii_with_both_transitions_in_range():
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("5000"),
        min_capacity=D("10"),  # 10g >= 100mg -> qualifies
        verification_type=VerificationType.INITIAL,
    )

    loads = [entry.L for entry in sequence]
    assert loads == sorted(loads)
    assert len(loads) == len(set(loads))  # distinct
    assert len(sequence) >= MIN_VERIFICATION_LOAD_COUNT

    assert D("5000") in loads
    assert D("10") in loads
    assert D("500") in loads
    assert D("2000") in loads

    by_L = {entry.L: entry for entry in sequence}
    assert by_L[D("5000")].kind is LoadKind.MAX
    assert by_L[D("10")].kind is LoadKind.MIN
    assert by_L[D("500")].kind is LoadKind.BAND_TRANSITION
    assert by_L[D("2000")].kind is LoadKind.BAND_TRANSITION

    # Band-transition MPE must match the engine's own lookup exactly (500e is
    # still Band 1's tolerance; 2000e is still Band 2's — see engine/mpe.py).
    assert by_L[D("500")].mpe == D("0.5")
    assert by_L[D("2000")].mpe == D("1.0")
    assert by_L[D("5000")].mpe == D("1.5")


def test_min_omitted_when_below_100mg():
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("5000"),
        min_capacity=D("0.05"),  # 50mg < 100mg -> must be omitted
        verification_type=VerificationType.INITIAL,
    )
    assert _by_kind(sequence, LoadKind.MIN) == []
    assert D("0.05") not in [entry.L for entry in sequence]


def test_min_omitted_when_none():
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("5000"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    assert _by_kind(sequence, LoadKind.MIN) == []


# ---------------------------------------------------------------------------
# Anchors alone are fewer than the target -> fill loads added to reach it,
# and they're tagged `fill` (never mistaken for a sourced anchor).
# ---------------------------------------------------------------------------
def test_fills_added_to_reach_minimum_count():
    # Max=300 is entirely inside Band 1 (first transition is 500) and Min is
    # omitted -> only one anchor (Max) exists; nine fills must be added to
    # reach the target of MIN_VERIFICATION_LOAD_COUNT.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("300"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )

    assert len(sequence) == MIN_VERIFICATION_LOAD_COUNT
    anchors = [entry for entry in sequence if entry.is_anchor]
    fills = _by_kind(sequence, LoadKind.FILL)
    assert len(anchors) == 1
    assert anchors[0].kind is LoadKind.MAX
    assert len(fills) == MIN_VERIFICATION_LOAD_COUNT - 1

    loads = [entry.L for entry in sequence]
    assert loads == sorted(loads)
    assert len(loads) == len(set(loads))
    for fill in fills:
        assert not fill.is_anchor


def test_fill_count_matches_shortfall_with_four_anchors():
    # Max=5000, Min=10 (qualifies), both transitions in range -> 4 anchors;
    # the shortfall against the target (MIN_VERIFICATION_LOAD_COUNT) is made
    # up with fills.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("5000"),
        min_capacity=D("10"),
        verification_type=VerificationType.INITIAL,
    )
    assert len(sequence) == MIN_VERIFICATION_LOAD_COUNT
    assert len(_by_kind(sequence, LoadKind.FILL)) == MIN_VERIFICATION_LOAD_COUNT - 4


# ---------------------------------------------------------------------------
# Project target is 10 (a lab convention exceeding OIML's 5-load minimum, not
# an OIML requirement of 10 itself — see engine/load_sequence.py docstring).
# A typical RRSL Class III instrument must reach that target.
# ---------------------------------------------------------------------------
def test_typical_class_iii_instrument_reaches_target_of_ten():
    # e=10, Max=30000, Min=200 -> anchors: Max(30000), Min(200), and both
    # in-range band transitions (5000, 20000) = 4 anchors; six fills needed
    # to reach the target of 10. This is the project's own "demo instrument"
    # (docs/architecture.md) — its exact fill values are asserted below,
    # not just their count, specifically to lock in the round-load fix.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("10"),
        max_capacity=D("30000"),
        min_capacity=D("200"),
        verification_type=VerificationType.INITIAL,
    )

    assert MIN_VERIFICATION_LOAD_COUNT == 10
    assert len(sequence) >= 10

    loads = [entry.L for entry in sequence]
    assert loads == sorted(loads)
    assert len(loads) == len(set(loads))  # distinct, no duplicates

    anchors = [entry for entry in sequence if entry.is_anchor]
    fills = _by_kind(sequence, LoadKind.FILL)
    assert len(anchors) == 4
    assert len(fills) == 6
    for fill in fills:
        assert not fill.is_anchor

    by_L = {entry.L: entry for entry in sequence}
    assert by_L[D("30000")].kind is LoadKind.MAX
    assert by_L[D("200")].kind is LoadKind.MIN
    assert by_L[D("5000")].kind is LoadKind.BAND_TRANSITION
    assert by_L[D("20000")].kind is LoadKind.BAND_TRANSITION

    # The anchors are exact and untouched by the fill-strategy change.
    assert {entry.L for entry in anchors} == {D("30000"), D("200"), D("5000"), D("20000")}

    # The fills are now ROUND values — deterministic multiples of a "nice"
    # step (500, this instrument's Band 1 span/count works out to a 500g
    # step) — never the repeating-decimal fractions
    # (885.714285714285714285714286, ...) the old even-fractional-spacing
    # strategy produced for a span/count combination like this one.
    fill_loads = {entry.L for entry in fills}
    assert fill_loads == {D("500"), D("1500"), D("2000"), D("3000"), D("3500"), D("4500")}
    for fill in fills:
        assert fill.L == fill.L.to_integral_value(), f"{fill.L} is not a round whole number"

    # Same inputs -> same output, every time.
    again = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("10"),
        max_capacity=D("30000"),
        min_capacity=D("200"),
        verification_type=VerificationType.INITIAL,
    )
    assert [entry.L for entry in again] == loads


# ---------------------------------------------------------------------------
# Round-fill fix: fills must snap to realistic, round load values — never
# the repeating-decimal fractions (885.714285714285714285714286, ...) the
# old even-fractional-spacing strategy produced. Anchors stay exactly as
# sourced; only the FILL points change.
# ---------------------------------------------------------------------------
def test_fills_are_round_whole_numbers_not_repeating_decimals():
    # Max=6200, e=1, no Min -> anchors: Max(6200) + both in-range transitions
    # (500, 2000) = 3 anchors; 7 fills needed, spread across [0, 500) — a
    # span/count combination (500/8 = 62.5) that under the OLD fractional
    # strategy would have produced eighths (62.5, 125, 187.5, ...).
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("6200"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    fills = _by_kind(sequence, LoadKind.FILL)
    assert len(fills) == 7
    for fill in fills:
        assert fill.L == fill.L.to_integral_value(), f"{fill.L} is not a round whole number"
        assert not fill.is_anchor


def test_fills_never_collide_with_or_duplicate_anchors():
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("10"),
        max_capacity=D("30000"),
        min_capacity=D("200"),
        verification_type=VerificationType.INITIAL,
    )
    anchor_loads = {entry.L for entry in sequence if entry.is_anchor}
    fill_loads = [entry.L for entry in sequence if not entry.is_anchor]
    assert anchor_loads.isdisjoint(fill_loads)
    assert len(fill_loads) == len(set(fill_loads))  # fills distinct from each other too


def test_fills_stay_strictly_inside_band_1():
    # Band 1 for Class III ends at m=500 -> L=500 (e=1) — every fill must be
    # strictly below that, and strictly above the lower bound (Min, here).
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("5000"),
        min_capacity=D("10"),
        verification_type=VerificationType.INITIAL,
    )
    fills = _by_kind(sequence, LoadKind.FILL)
    assert len(fills) > 0
    for fill in fills:
        assert D("10") < fill.L < D("500")


def test_round_fill_still_reaches_target_when_whole_range_is_band_1():
    # Max=300 (no Min) sits entirely inside Band 1 (first transition is
    # 500) -> only one anchor; the round-step fix must still reach the
    # target of 10 loads, same as the old fractional strategy did.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("300"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    assert len(sequence) == MIN_VERIFICATION_LOAD_COUNT
    fills = _by_kind(sequence, LoadKind.FILL)
    assert len(fills) == MIN_VERIFICATION_LOAD_COUNT - 1
    for fill in fills:
        assert fill.L == fill.L.to_integral_value()
        assert D("0") < fill.L < D("300")


def test_round_fill_is_deterministic():
    kwargs = dict(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("6200"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    first = [entry.L for entry in generate_load_sequence(**kwargs)]
    second = [entry.L for entry in generate_load_sequence(**kwargs)]
    assert first == second


# ---------------------------------------------------------------------------
# Determinism: no randomness, ever.
# ---------------------------------------------------------------------------
def test_determinism_same_inputs_same_output():
    kwargs = dict(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("300"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    first = generate_load_sequence(**kwargs)
    second = generate_load_sequence(**kwargs)

    assert [entry.L for entry in first] == [entry.L for entry in second]
    assert [entry.kind for entry in first] == [entry.kind for entry in second]
    assert [entry.mpe for entry in first] == [entry.mpe for entry in second]


# ---------------------------------------------------------------------------
# Edge: a band transition beyond Max is excluded — only in-range ones appear.
# ---------------------------------------------------------------------------
def test_band_transition_beyond_max_is_excluded():
    # Class III's first transition is 500e; Max=300 is below it.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("300"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    assert _by_kind(sequence, LoadKind.BAND_TRANSITION) == []
    assert all(entry.L <= D("300") for entry in sequence)


def test_only_in_range_transition_included_when_max_is_between_them():
    # Max=1000 is above the first transition (500) but below the second (2000).
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("1000"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    transitions = {entry.L for entry in _by_kind(sequence, LoadKind.BAND_TRANSITION)}
    assert transitions == {D("500")}


# ---------------------------------------------------------------------------
# No silent defaults.
# ---------------------------------------------------------------------------
def test_requires_every_argument_except_min_capacity():
    valid = dict(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("5000"),
        min_capacity=D("10"),
        verification_type=VerificationType.INITIAL,
    )
    for missing in ["accuracy_class", "e", "max_capacity", "verification_type"]:
        kwargs = {k: v for k, v in valid.items() if k != missing}
        with pytest.raises(TypeError):
            generate_load_sequence(**kwargs)

    # min_capacity is the one argument allowed to be omitted (as None).
    kwargs = {k: v for k, v in valid.items() if k != "min_capacity"}
    generate_load_sequence(**kwargs, min_capacity=None)


def test_rejects_float_instead_of_decimal():
    with pytest.raises(TypeError):
        generate_load_sequence(
            accuracy_class=AccuracyClass.III,
            e=1.0,
            max_capacity=D("5000"),
            min_capacity=D("10"),
            verification_type=VerificationType.INITIAL,
        )
