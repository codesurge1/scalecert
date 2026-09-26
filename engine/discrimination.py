"""Discrimination test — R76-2 page 14, "4.1 Discrimination" — THREE
distinct sub-procedures, selected by the instrument's `indication_type`, not
one formula with variants bolted on:

  - Analog (A.4.8.1): apply L, read I1; apply an extra load = |mpe|, read
    I2. Pass: I2 - I1 >= 0.7 * mpe.
  - Non-self-indicating (A.4.8.1): apply L; apply an extra load = 0.4*|mpe|;
    observe whether there is a visible displacement. Pass is qualitative —
    a Yes/No observation, not a computed threshold.
  - Digital (A.4.8.2): apply L, read I1; remove the load, re-add it in
    1/10 d increments up to 1.4d, read I2. Pass: I2 - I1 >= d. This variant
    is NOT required for verification of digital-indication instruments per
    clause 8.3.3 — implemented here for spec completeness (the frontend
    gates the whole Discrimination test N/A for digital instruments); it
    needs no mpe/accuracy_class/verification_type at all, unlike the other
    two.

Standard library only — no third-party imports; all arithmetic Decimal.
"""

from decimal import Decimal
from typing import Optional

from engine.mpe import lookup_mpe
from engine.types import (
    AccuracyClass,
    DiscriminationAnalogResult,
    DiscriminationDigitalResult,
    DiscriminationNonSelfIndicatingResult,
    VerificationType,
)

ANALOG_THRESHOLD_FRACTION = Decimal("0.7")
NON_SELF_INDICATING_EXTRA_LOAD_FRACTION = Decimal("0.4")

# Three check loads (matching the 3 blank rows on each of page 14's three
# sub-tables): an anchor near the low end (min_capacity if known, else a
# fraction of Max), the midpoint, and Max — a documented convention (like
# load_sequence.py's FILL_SPACING_STRATEGY), pending RRSL confirmation, not
# an OIML-sourced figure.
_LOW_ANCHOR_FALLBACK_FRACTION_OF_MAX = Decimal("0.1")


def _require_decimal(name: str, value) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    return value


def generate_discrimination_checks(*, max_capacity: Decimal, min_capacity: Optional[Decimal]) -> list[Decimal]:
    max_capacity = _require_decimal("max_capacity", max_capacity)
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")
    if min_capacity is not None:
        min_capacity = _require_decimal("min_capacity", min_capacity)
        if min_capacity < 0:
            raise ValueError(f"min_capacity must be >= 0, got {min_capacity}")

    low = min_capacity if (min_capacity is not None and min_capacity > 0) else max_capacity * _LOW_ANCHOR_FALLBACK_FRACTION_OF_MAX
    return [low, max_capacity / 2, max_capacity]


def compute_discrimination_analog(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    L: Decimal,
    I1: Decimal,
    I2: Decimal,
) -> DiscriminationAnalogResult:
    if not isinstance(accuracy_class, AccuracyClass):
        raise TypeError(f"accuracy_class must be an AccuracyClass, got {type(accuracy_class).__name__}")
    if not isinstance(verification_type, VerificationType):
        raise TypeError(f"verification_type must be a VerificationType, got {type(verification_type).__name__}")
    e = _require_decimal("e", e)
    L = _require_decimal("L", L)
    I1 = _require_decimal("I1", I1)
    I2 = _require_decimal("I2", I2)
    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if L < 0:
        raise ValueError(f"L must be >= 0, got {L}")

    mpe_lookup = lookup_mpe(accuracy_class=accuracy_class, m=L / e, e=e, verification_type=verification_type)
    mpe = mpe_lookup.mpe_grams
    difference = I2 - I1
    threshold = ANALOG_THRESHOLD_FRACTION * mpe

    return DiscriminationAnalogResult(
        L=L, mpe=mpe, mpe_lookup=mpe_lookup, I1=I1, I2=I2, difference=difference, threshold=threshold,
        passed=difference >= threshold,
    )


def compute_discrimination_non_self_indicating(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    L: Decimal,
    visible_displacement: bool,
) -> DiscriminationNonSelfIndicatingResult:
    if not isinstance(accuracy_class, AccuracyClass):
        raise TypeError(f"accuracy_class must be an AccuracyClass, got {type(accuracy_class).__name__}")
    if not isinstance(verification_type, VerificationType):
        raise TypeError(f"verification_type must be a VerificationType, got {type(verification_type).__name__}")
    if not isinstance(visible_displacement, bool):
        raise TypeError(f"visible_displacement must be a bool, got {type(visible_displacement).__name__}")
    e = _require_decimal("e", e)
    L = _require_decimal("L", L)
    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if L < 0:
        raise ValueError(f"L must be >= 0, got {L}")

    mpe_lookup = lookup_mpe(accuracy_class=accuracy_class, m=L / e, e=e, verification_type=verification_type)
    mpe = mpe_lookup.mpe_grams
    extra_load = NON_SELF_INDICATING_EXTRA_LOAD_FRACTION * mpe

    return DiscriminationNonSelfIndicatingResult(
        L=L, mpe=mpe, mpe_lookup=mpe_lookup, extra_load=extra_load,
        visible_displacement=visible_displacement, passed=visible_displacement,
    )


def compute_discrimination_digital(*, L: Decimal, d: Decimal, I1: Decimal, I2: Decimal) -> DiscriminationDigitalResult:
    L = _require_decimal("L", L)
    d = _require_decimal("d", d)
    I1 = _require_decimal("I1", I1)
    I2 = _require_decimal("I2", I2)
    if L < 0:
        raise ValueError(f"L must be >= 0, got {L}")
    if d <= 0:
        raise ValueError(f"d must be > 0, got {d}")

    difference = I2 - I1
    return DiscriminationDigitalResult(L=L, d=d, I1=I1, I2=I2, difference=difference, passed=difference >= d)
