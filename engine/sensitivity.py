"""Sensitivity test — R76-2 page 15, "4.2 Sensitivity (non-self-indicating
instrument) (A.4.9)". Applies only to non-self-indicating instruments
(clause 6.1). Apply L; apply an extra load = |mpe|; measure the permanent
displacement of the indicating element in mm.

Pass threshold is TIERED by accuracy class AND Max — not a single fixed
number:
  - class I or II: >= 1 mm
  - class III or IIII with Max <= 30 kg: >= 2 mm
  - class III or IIII with Max > 30 kg: >= 5 mm
`max_capacity` is stored in grams throughout this app, so the 30 kg
boundary is compared as 30000 g.

Standard library only — no third-party imports; all arithmetic Decimal.
"""

from decimal import Decimal
from typing import Optional

from engine.mpe import lookup_mpe
from engine.types import AccuracyClass, SensitivityResult, VerificationType

MAX_THRESHOLD_GRAMS = Decimal("30000")  # 30 kg, in grams (max_capacity's unit)

_TIER_1_2_MM = Decimal("1")
_TIER_LOW_MAX_MM = Decimal("2")
_TIER_HIGH_MAX_MM = Decimal("5")

# Three check loads, same convention/rationale as
# engine.discrimination.generate_discrimination_checks (a documented
# convention pending RRSL confirmation, matching page 15's 3 blank rows).
_LOW_ANCHOR_FALLBACK_FRACTION_OF_MAX = Decimal("0.1")


def _require_decimal(name: str, value) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    return value


def generate_sensitivity_checks(*, max_capacity: Decimal, min_capacity: Optional[Decimal]) -> list[Decimal]:
    max_capacity = _require_decimal("max_capacity", max_capacity)
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")
    if min_capacity is not None:
        min_capacity = _require_decimal("min_capacity", min_capacity)
        if min_capacity < 0:
            raise ValueError(f"min_capacity must be >= 0, got {min_capacity}")

    low = min_capacity if (min_capacity is not None and min_capacity > 0) else max_capacity * _LOW_ANCHOR_FALLBACK_FRACTION_OF_MAX
    return [low, max_capacity / 2, max_capacity]


def sensitivity_threshold_mm(*, accuracy_class: AccuracyClass, max_capacity: Decimal) -> Decimal:
    if not isinstance(accuracy_class, AccuracyClass):
        raise TypeError(f"accuracy_class must be an AccuracyClass, got {type(accuracy_class).__name__}")
    max_capacity = _require_decimal("max_capacity", max_capacity)
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")

    if accuracy_class in (AccuracyClass.I, AccuracyClass.II):
        return _TIER_1_2_MM
    return _TIER_LOW_MAX_MM if max_capacity <= MAX_THRESHOLD_GRAMS else _TIER_HIGH_MAX_MM


def compute_sensitivity(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    max_capacity: Decimal,
    L: Decimal,
    permanent_displacement_mm: Decimal,
) -> SensitivityResult:
    if not isinstance(verification_type, VerificationType):
        raise TypeError(f"verification_type must be a VerificationType, got {type(verification_type).__name__}")
    e = _require_decimal("e", e)
    L = _require_decimal("L", L)
    permanent_displacement_mm = _require_decimal("permanent_displacement_mm", permanent_displacement_mm)
    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if L < 0:
        raise ValueError(f"L must be >= 0, got {L}")
    if permanent_displacement_mm < 0:
        raise ValueError(f"permanent_displacement_mm must be >= 0, got {permanent_displacement_mm}")

    mpe_lookup = lookup_mpe(accuracy_class=accuracy_class, m=L / e, e=e, verification_type=verification_type)
    mpe = mpe_lookup.mpe_grams
    threshold_mm = sensitivity_threshold_mm(accuracy_class=accuracy_class, max_capacity=max_capacity)

    return SensitivityResult(
        L=L,
        mpe=mpe,
        mpe_lookup=mpe_lookup,
        extra_load=abs(mpe),
        permanent_displacement_mm=permanent_displacement_mm,
        threshold_mm=threshold_mm,
        passed=permanent_displacement_mm >= threshold_mm,
    )
