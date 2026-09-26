"""Repeatability test — R76-1 A.4.5 / A.4.10 (R76-2 page 16, "5 REPEATABILITY
(A.4.10)"). Structurally DIFFERENT from Weighing, not a clone:

  - Two independent series of readings, each at ONE FIXED load (not a
    load sequence): series 1 at ~50% of Max, series 2 at ~100% of Max (Max
    itself) — R76-1's own two representative test loads for this test.
    Nominally 10 readings per series (R76-2 page 16's own row count).
  - E = I + 1/2*e - deltaL - L — NO E0 correction. This is deliberate, per
    R76-1 A.4.5's own construction of the test (page 16 has no E0/Ec
    columns at all, only a single "Error, E" column) — do not add one.
  - Two pass criteria, checked per series independently:
      a) every individual reading's |E| <= mpe
      b) the spread across the series, Emax - Emin (signed E, not |E|),
         <= mpe
    A series passes only if both hold. Each series has its own mpe, since
    the two series are tested at different loads (different Table 6 bands
    are possible, though not guaranteed, for the same instrument).

Standard library only — no third-party imports; all arithmetic Decimal.
"""

from decimal import Decimal
from typing import Sequence, Tuple

from engine.mpe import lookup_mpe
from engine.types import (
    AccuracyClass,
    RepeatabilityReadingResult,
    RepeatabilitySeriesResult,
    VerificationType,
)

HALF = Decimal("0.5")

# Series 1 is tested at ~50% of Max, series 2 at ~100% of Max (Max itself) —
# R76-1 A.4.5's own two representative test loads (R76-2 page 16: "Load
# (weighing 1-10)" / "Load (weighing 11-20)", one fixed load per block of
# readings).
SERIES_LOAD_FRACTIONS = {1: Decimal("0.5"), 2: Decimal("1")}


def _require_decimal(name: str, value) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    return value


def generate_repeatability_load(*, series_no: int, max_capacity: Decimal) -> Decimal:
    """The fixed load for a Repeatability series — server-derived, never
    technician-entered (same discipline as Weighing's auto-generated `L`)."""
    if series_no not in SERIES_LOAD_FRACTIONS:
        raise ValueError(f"series_no must be 1 or 2, got {series_no}")
    max_capacity = _require_decimal("max_capacity", max_capacity)
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")
    return max_capacity * SERIES_LOAD_FRACTIONS[series_no]


def compute_repeatability_series(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    series_no: int,
    L: Decimal,
    readings: Sequence[Tuple[Decimal, Decimal]],
) -> RepeatabilitySeriesResult:
    """Compute the full derivation for one series from its raw (I, delta_l)
    reading pairs, in submission order. Unlike Weighing's per-reading engine
    call, this takes the WHOLE series at once — the spread criterion
    (Emax - Emin) is inherently a property of the full set of readings, not
    any single one, so there is no meaningful "per-reading" engine call here.
    """
    if not isinstance(accuracy_class, AccuracyClass):
        raise TypeError(f"accuracy_class must be an AccuracyClass, got {type(accuracy_class).__name__}")
    if not isinstance(verification_type, VerificationType):
        raise TypeError(f"verification_type must be a VerificationType, got {type(verification_type).__name__}")
    if series_no not in SERIES_LOAD_FRACTIONS:
        raise ValueError(f"series_no must be 1 or 2, got {series_no}")

    e = _require_decimal("e", e)
    L = _require_decimal("L", L)
    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if L < 0:
        raise ValueError(f"L must be >= 0, got {L}")
    if not readings:
        raise ValueError("readings must be non-empty")

    m = L / e
    mpe_lookup = lookup_mpe(accuracy_class=accuracy_class, m=m, e=e, verification_type=verification_type)
    mpe = mpe_lookup.mpe_grams

    reading_results = []
    for I, delta_l in readings:
        I = _require_decimal("I", I)
        delta_l = _require_decimal("delta_l", delta_l)
        E = I + HALF * e - delta_l - L
        reading_results.append(RepeatabilityReadingResult(I=I, delta_l=delta_l, E=E, within_mpe=abs(E) <= mpe))

    e_values = [r.E for r in reading_results]
    e_max = max(e_values)
    e_min = min(e_values)
    spread = e_max - e_min
    all_within_mpe = all(r.within_mpe for r in reading_results)
    spread_within_mpe = spread <= mpe

    return RepeatabilitySeriesResult(
        series_no=series_no,
        L=L,
        mpe=mpe,
        mpe_lookup=mpe_lookup,
        readings=tuple(reading_results),
        e_max=e_max,
        e_min=e_min,
        spread=spread,
        all_within_mpe=all_within_mpe,
        spread_within_mpe=spread_within_mpe,
        passed=all_within_mpe and spread_within_mpe,
    )
