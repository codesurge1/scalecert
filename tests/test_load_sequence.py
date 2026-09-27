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
    # omitted -> Max plus the 10e start anchor (=10, well below 300) are the
    # only two anchors; eight fills must be added to reach the target of
    # MIN_VERIFICATION_LOAD_COUNT.
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
    assert len(anchors) == 2
    assert {entry.kind for entry in anchors} == {LoadKind.MAX, LoadKind.TEN_E}
    assert len(fills) == MIN_VERIFICATION_LOAD_COUNT - 2

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
    # e=10, Max=30000, Min=200 -> anchors: the 10e start anchor (100), Min
    # (200), both in-range band transitions (5000, 20000), and Max (30000) =
    # 5 anchors; five fills needed to reach the target of 10. This is the
    # project's own "demo instrument" (docs/architecture.md) — its exact
    # anchor/fill values are asserted below, not just their counts,
    # specifically to lock in the round-load fix and the 10e-start addition.
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

    # 10e (=100) is the lowest load in the sequence, per the RRSL start
    # convention this task adds.
    assert loads[0] == D("100")

    anchors = [entry for entry in sequence if entry.is_anchor]
    fills = _by_kind(sequence, LoadKind.FILL)
    assert len(anchors) == 5
    assert len(fills) == 5
    for fill in fills:
        assert not fill.is_anchor

    by_L = {entry.L: entry for entry in sequence}
    assert by_L[D("100")].kind is LoadKind.TEN_E
    assert by_L[D("30000")].kind is LoadKind.MAX
    assert by_L[D("200")].kind is LoadKind.MIN
    assert by_L[D("5000")].kind is LoadKind.BAND_TRANSITION
    assert by_L[D("20000")].kind is LoadKind.BAND_TRANSITION

    # The anchors are exact and untouched by the fill-strategy change.
    assert {entry.L for entry in anchors} == {D("100"), D("30000"), D("200"), D("5000"), D("20000")}

    # The fills are ROUND values — deterministic multiples of a "nice" step
    # — never the repeating-decimal fractions
    # (885.714285714285714285714286, ...) the old even-fractional-spacing
    # strategy produced for a span/count combination like this one.
    fill_loads = {entry.L for entry in fills}
    assert fill_loads == {D("1000"), D("1500"), D("2500"), D("3500"), D("4000")}
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
    assert [entry.kind for entry in again] == [entry.kind for entry in sequence]


# ---------------------------------------------------------------------------
# Round-fill fix: fills must snap to realistic, round load values — never
# the repeating-decimal fractions (885.714285714285714285714286, ...) the
# old even-fractional-spacing strategy produced. Anchors stay exactly as
# sourced; only the FILL points change.
# ---------------------------------------------------------------------------
def test_fills_are_round_whole_numbers_not_repeating_decimals():
    # Max=6200, e=1, no Min -> anchors: Max(6200), both in-range transitions
    # (500, 2000), and the 10e start anchor (10) = 4 anchors; 6 fills needed.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("6200"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    fills = _by_kind(sequence, LoadKind.FILL)
    assert len(fills) == 6
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
    # 500) -> Max plus the 10e start anchor (=10) are the only two anchors;
    # the round-step fix must still reach the target of 10 loads, same as
    # the old fractional strategy did.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("300"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    assert len(sequence) == MIN_VERIFICATION_LOAD_COUNT
    fills = _by_kind(sequence, LoadKind.FILL)
    assert len(fills) == MIN_VERIFICATION_LOAD_COUNT - 2
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
# 10e start anchor (RRSL lab convention, not OIML-sourced — see module
# docstring): the load run's first (lowest) load is ten verification scale
# intervals, tagged LoadKind.TEN_E.
# ---------------------------------------------------------------------------
def test_ten_e_is_the_first_load():
    # e=10, Max=30000, Min=200 (the demo instrument) -> 10e = 100, well
    # below Min (200) and every other anchor, so it must sort to the front.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("10"),
        max_capacity=D("30000"),
        min_capacity=D("200"),
        verification_type=VerificationType.INITIAL,
    )
    assert sequence[0].L == D("100")
    assert sequence[0].kind is LoadKind.TEN_E
    assert sequence[0].is_anchor


def test_ten_e_dedupes_when_equal_to_min():
    # e=1, Min=10 -> 10e = 10 = Min exactly. Must not produce two entries at
    # the same load; the OIML-sourced Min anchor wins the tie, not a
    # duplicate ten_e-kind entry.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("1"),
        max_capacity=D("5000"),
        min_capacity=D("10"),
        verification_type=VerificationType.INITIAL,
    )
    loads = [entry.L for entry in sequence]
    assert loads.count(D("10")) == 1
    by_L = {entry.L: entry for entry in sequence}
    assert by_L[D("10")].kind is LoadKind.MIN
    assert _by_kind(sequence, LoadKind.TEN_E) == []
    # Anchor count is unaffected by the dedupe: Min, both transitions, Max.
    assert len([entry for entry in sequence if entry.is_anchor]) == 4


def test_ten_e_skipped_when_it_would_exceed_max():
    # e=10 -> 10e = 100, but Max=50 here (a tiny-range instrument): adding a
    # load above Max would be nonsensical, so ten_e must be skipped
    # entirely rather than added or clamped.
    sequence = generate_load_sequence(
        accuracy_class=AccuracyClass.III,
        e=D("10"),
        max_capacity=D("50"),
        min_capacity=None,
        verification_type=VerificationType.INITIAL,
    )
    assert _by_kind(sequence, LoadKind.TEN_E) == []
    assert D("100") not in [entry.L for entry in sequence]
    assert all(entry.L <= D("50") for entry in sequence)
    # The sequence still reaches the target via Max + fills alone.
    assert len(sequence) == MIN_VERIFICATION_LOAD_COUNT


def test_ten_e_is_deterministic():
    kwargs = dict(
        accuracy_class=AccuracyClass.III,
        e=D("10"),
        max_capacity=D("30000"),
        min_capacity=D("200"),
        verification_type=VerificationType.INITIAL,
    )
    first = generate_load_sequence(**kwargs)
    second = generate_load_sequence(**kwargs)
    assert [entry.L for entry in first] == [entry.L for entry in second]
    assert [entry.kind for entry in first] == [entry.kind for entry in second]
    assert first[0].kind is LoadKind.TEN_E
    assert second[0].kind is LoadKind.TEN_E


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
