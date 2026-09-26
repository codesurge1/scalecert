"""Deterministic load-sequence generator for the Weighing test (R76-1 A.4.4-A.4.6).

Produces the sequence of applied loads L a Weighing test must cover, so the
technician enters only Indication (I) and additional load (deltaL) at each
load — never L itself (CLAUDE.md).

Verification load count — two distinct numbers, do not conflate them:
  - The OIML clause 8.3.3 verification checklist this project implements has
    a SOURCED MINIMUM of >=5 distinct test loads. That minimum is fixed by
    the standard and does not change.
  - This project's own TARGET is 10 distinct test loads
    (MIN_VERIFICATION_LOAD_COUNT) — a LAB CONVENTION, not an OIML
    requirement. Spreading more load points across the range gives a more
    thorough verification and matches common RRSL practice; OIML itself only
    requires 5. It is a coincidence of numbering, not the same figure, that
    a DIFFERENT ">=10" also appears in some visit-report material for FULL
    TYPE EVALUATION (the complete intrinsic-error test battery — a separate,
    out-of-scope regime per CLAUDE.md). This module's 10 is never sourced
    from, or a stand-in for, that figure.

Sourced anchors (mandatory, always present when applicable):
  - Max (the instrument's maximum capacity).
  - Min, but ONLY if given AND >= 100 mg (0.1 g) — A.4.4.1. A None or
    sub-100mg Min is omitted, not clamped or guessed.
  - Every MPE band-transition load (R76-1 Table 6) that falls within
    [Min-or-0, Max] — these are where the tolerance changes, so a
    verification must include them. Pulled directly from engine.mpe.
    BAND_TABLE (the same table lookup_mpe uses) — never a second, hardcoded
    copy of the band edges.

OPEN ITEM — Band-1 fill spacing (docs/plan.md "Open questions"): OIML does
not prescribe how many additional loads, or where, to place strictly inside
Band 1 (below the first in-range band transition, or below Max if the whole
range sits in Band 1) beyond the mandatory anchors, and RRSL has not yet
confirmed a convention. When the mandatory anchors are fewer than
MIN_VERIFICATION_LOAD_COUNT, this module fills the gap with EVENLY SPACED
points inside Band 1. That choice is a documented, deterministic PLACEHOLDER
CONVENTION — not an OIML requirement — labeled by FILL_SPACING_STRATEGY below
so it is a one-line change once RRSL confirms an actual convention. Every
generated load is tagged with its `kind` (LoadEntry.is_anchor), so a fill
point can never be mistaken downstream (report, UI) for a sourced one.

Bidirectional testing: the plan requires each load tested going up AND
coming back down. This generator returns only the DISTINCT ascending load
values — expanding each into an "up" and "down" reading is left to the
reading layer (Phase 2 concern), not duplicated here.

Standard library only — no third-party imports (same purity guardrail as
the rest of engine/).
"""

from decimal import Decimal
from typing import List, Optional

from engine.mpe import BAND_TABLE, lookup_mpe
from engine.types import AccuracyClass, LoadEntry, LoadKind, VerificationType

# Project target, a lab convention: 10 distinct loads. The OIML 8.3.3
# sourced minimum is 5 (unchanged); 10 exceeds it for more thorough coverage
# across the range, matching common RRSL practice — it is NOT itself an OIML
# requirement, and it is NOT the unrelated >=10 of full type evaluation (a
# different, out-of-scope test battery) — see module docstring.
MIN_VERIFICATION_LOAD_COUNT = 10

# A.4.4.1: Min is a mandatory anchor only at or above 100 mg (0.1 g).
MIN_CAPACITY_THRESHOLD_GRAMS = Decimal("0.1")

# PLACEHOLDER pending RRSL confirmation (see module docstring) — not OIML-sourced.
# Changing the fill convention later should mean changing this label and the
# one function it names below, nothing else in this module.
FILL_SPACING_STRATEGY = "even_spacing_within_band_1"


def _require_decimal(name: str, value) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    return value


def _make_entry(
    L: Decimal,
    e: Decimal,
    kind: LoadKind,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
) -> LoadEntry:
    m = L / e
    mpe_lookup = lookup_mpe(
        accuracy_class=accuracy_class,
        m=m,
        e=e,
        verification_type=verification_type,
    )
    return LoadEntry(L=L, m=m, kind=kind, mpe=mpe_lookup.mpe_grams, mpe_lookup=mpe_lookup)


def _band_transition_loads_m(accuracy_class: AccuracyClass) -> List[Decimal]:
    """The m-value at every Table 6 band boundary EXCEPT the last row's — the
    last row's upper bound (finite or unbounded) is the top of the table's
    domain, not a transition to a further band. Reuses engine.mpe.BAND_TABLE
    directly; this module holds no second copy of the band edges."""
    bands = BAND_TABLE[accuracy_class]
    return [upper for upper, _ in bands[:-1] if upper is not None]


def _even_spacing_within_band_1(
    lower_bound: Decimal,
    band1_upper: Decimal,
    count: int,
) -> List[Decimal]:
    """The placeholder fill strategy named by FILL_SPACING_STRATEGY: `count`
    points spaced evenly in the open interval (lower_bound, band1_upper).
    Deterministic and reproducible — never random — but NOT OIML-sourced."""
    span = band1_upper - lower_bound
    if span <= 0:
        return []
    return [lower_bound + span * Decimal(i) / Decimal(count + 1) for i in range(1, count + 1)]


def generate_load_sequence(
    *,
    accuracy_class: AccuracyClass,
    e: Decimal,
    max_capacity: Decimal,
    min_capacity: Optional[Decimal],
    verification_type: VerificationType,
) -> List[LoadEntry]:
    """Generate the deterministic, reproducible sequence of applied loads for
    a Weighing test verification. No silent defaults: every argument is
    required and type-checked explicitly; `min_capacity` is the sole
    genuinely optional argument (explicitly `Optional[Decimal]`, not a
    default value) since an instrument may have no documented Min.

    Returns a list of `LoadEntry`, sorted ascending by `L`, distinct, each
    carrying `L`, `m`, `kind`, and the `mpe` that applies at that load.
    """
    if not isinstance(accuracy_class, AccuracyClass):
        raise TypeError(f"accuracy_class must be an AccuracyClass, got {type(accuracy_class).__name__}")
    if not isinstance(verification_type, VerificationType):
        raise TypeError(f"verification_type must be a VerificationType, got {type(verification_type).__name__}")

    e = _require_decimal("e", e)
    max_capacity = _require_decimal("max_capacity", max_capacity)
    if min_capacity is not None:
        min_capacity = _require_decimal("min_capacity", min_capacity)

    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")
    if min_capacity is not None and min_capacity < 0:
        raise ValueError(f"min_capacity must be >= 0, got {min_capacity}")
    if min_capacity is not None and min_capacity > max_capacity:
        raise ValueError(f"min_capacity ({min_capacity}) must be <= max_capacity ({max_capacity})")

    # A.4.4.1: Min is a mandatory anchor only at or above 100 mg; otherwise omitted.
    effective_min = (
        min_capacity
        if min_capacity is not None and min_capacity >= MIN_CAPACITY_THRESHOLD_GRAMS
        else None
    )
    lower_bound = effective_min if effective_min is not None else Decimal("0")

    anchors: List[LoadEntry] = []
    seen_L = set()

    def _add_anchor(L: Decimal, kind: LoadKind) -> None:
        if L in seen_L:
            return  # an earlier anchor already claimed this exact load
        seen_L.add(L)
        anchors.append(_make_entry(L, e, kind, accuracy_class, verification_type))

    _add_anchor(max_capacity, LoadKind.MAX)
    if effective_min is not None:
        _add_anchor(effective_min, LoadKind.MIN)
    for upper_m in _band_transition_loads_m(accuracy_class):
        L = upper_m * e
        if lower_bound <= L <= max_capacity:
            _add_anchor(L, LoadKind.BAND_TRANSITION)

    anchors.sort(key=lambda entry: entry.L)

    needed = MIN_VERIFICATION_LOAD_COUNT - len(anchors)
    fills: List[LoadEntry] = []
    if needed > 0:
        # Band 1 spans [lower_bound, band1_upper): band1_upper is the
        # smallest in-range band transition, or max_capacity if the whole
        # range sits inside Band 1 (no transition applies within
        # [lower_bound, Max]) — see FILL_SPACING_STRATEGY above.
        in_range_transitions = sorted(
            entry.L for entry in anchors if entry.kind is LoadKind.BAND_TRANSITION
        )
        band1_upper = in_range_transitions[0] if in_range_transitions else max_capacity

        for candidate in _even_spacing_within_band_1(lower_bound, band1_upper, needed):
            if candidate in seen_L:
                continue  # an anchor already sits exactly here — keep the anchor
            seen_L.add(candidate)
            fills.append(_make_entry(candidate, e, LoadKind.FILL, accuracy_class, verification_type))
        # If Band 1 has no span (a degenerate instrument range) there is no
        # room to place fill points, and the sequence may fall short of
        # MIN_VERIFICATION_LOAD_COUNT. Not exercised by any real instrument
        # in this project's scope.

    sequence = anchors + fills
    sequence.sort(key=lambda entry: entry.L)
    return sequence
