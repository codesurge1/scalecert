"""Tilting test — R76-2 page 20, "8 TILTING (A.5.1, A.5.1.1-A.5.1.3)" — the
minimal 8.3.3/4.18 slice, not the full Annex A.5.1 battery: reference
position (1) plus 4 tilted positions (2-5), each tested unloaded (to
establish that position's own E0), then at two loads (a mid load and Max).
Applies to mobile instruments only (clause 4.18).

  Ev = Iv + 1/2*e - deltaLv - L   (v = 1..5, one per tilt position)
  Ecv = Ev - Ev0

Both formulas are IDENTICAL to Weighing's, so every reading in this module
is computed via engine.weighing.compute_weighing_result — never
reimplemented. The one genuine structural difference from Eccentricity:
here E0 is measured ONCE per position (from that position's own unloaded
reading, L=0) and reused for BOTH of that position's loaded readings —
Eccentricity re-measures E0 fresh before every single reading.

Two independent pass criteria:
  a) unloaded: |E1,0 - Ev,0|_max <= 2e across whichever positions have been
     measured (position 1, the reference, must be among them). NOT modeled:
     the standard's own "(not valid for class II instruments, if not used
     for direct sales to the public)" carve-out — `instruments` has no
     direct-sale flag; flagged as a known gap, not silently ignored.
  b) loaded, checked independently at EACH loaded row (mid load and Max):
     |Ec1 - Ecv|_max <= mpe for that row's own load — mirrors
     Repeatability's "each series/row gets its own mpe" principle, since the
     two loads can land in different Table 6 bands.

Standard library only — no third-party imports; all arithmetic Decimal.
"""

from decimal import Decimal
from typing import Dict

from engine.mpe import lookup_mpe
from engine.types import (
    AccuracyClass,
    TiltingLoadedCheckResult,
    TiltingUnloadedCheckResult,
    VerificationType,
    WeighingResult,
)
from engine.weighing import compute_weighing_result

# 1 = reference position, 2-5 = tilted positions (page 20's own numbering).
TILT_POSITIONS = (1, 2, 3, 4, 5)
REFERENCE_POSITION = 1

UNLOADED_LIMIT_MULTIPLE_OF_E = Decimal("2")

# The mid load's own value has no OIML-sourced figure on the paper form
# (its "L =" box is blank, filled in by the lab) — a documented convention,
# same status as engine.eccentricity's ~1/3-Max load: ~50% of Max, matching
# Repeatability's own series-1 convention for a "representative partial
# load", pending RRSL confirmation.
_MID_LOAD_FRACTION_OF_MAX = Decimal("0.5")


def _require_decimal(name: str, value) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    return value


def generate_tilting_mid_load(*, max_capacity: Decimal) -> Decimal:
    max_capacity = _require_decimal("max_capacity", max_capacity)
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")
    return max_capacity * _MID_LOAD_FRACTION_OF_MAX


def compute_tilt_unloaded_reading(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    I: Decimal,
    delta_l: Decimal,
) -> WeighingResult:
    """The unloaded reading at one position — L=0, E0=0, so `.E` (== `.Ec`)
    IS that position's Ev0 baseline, ready to feed into a loaded reading's
    own `E0` argument."""
    return compute_weighing_result(
        accuracy_class=accuracy_class, verification_type=verification_type, e=e,
        L=Decimal("0"), I=I, delta_l=delta_l, E0=Decimal("0"),
    )


def compute_tilt_loaded_reading(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    L: Decimal,
    I: Decimal,
    delta_l: Decimal,
    E0: Decimal,
) -> WeighingResult:
    """A loaded reading at one position — `E0` is THIS position's own Ev0
    (from its unloaded reading), so `.Ec` IS Ecv."""
    return compute_weighing_result(
        accuracy_class=accuracy_class, verification_type=verification_type, e=e,
        L=L, I=I, delta_l=delta_l, E0=E0,
    )


def compute_tilting_unloaded_check(*, e: Decimal, position_e0s: Dict[int, Decimal]) -> TiltingUnloadedCheckResult:
    e = _require_decimal("e", e)
    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if not position_e0s:
        raise ValueError("position_e0s must be non-empty")
    if REFERENCE_POSITION not in position_e0s:
        raise ValueError(f"position_e0s must include the reference position ({REFERENCE_POSITION})")
    for position_no, value in position_e0s.items():
        if position_no not in TILT_POSITIONS:
            raise ValueError(f"position_no must be one of {TILT_POSITIONS}, got {position_no}")
        _require_decimal("position_e0s value", value)

    reference = position_e0s[REFERENCE_POSITION]
    max_abs_deviation = max(abs(reference - value) for value in position_e0s.values())
    limit = UNLOADED_LIMIT_MULTIPLE_OF_E * e

    return TiltingUnloadedCheckResult(
        reference_e0=reference, max_abs_deviation=max_abs_deviation, limit=limit,
        within_limit=max_abs_deviation <= limit,
    )


def compute_tilting_loaded_check(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    L: Decimal,
    position_ecs: Dict[int, Decimal],
) -> TiltingLoadedCheckResult:
    if not isinstance(accuracy_class, AccuracyClass):
        raise TypeError(f"accuracy_class must be an AccuracyClass, got {type(accuracy_class).__name__}")
    if not isinstance(verification_type, VerificationType):
        raise TypeError(f"verification_type must be a VerificationType, got {type(verification_type).__name__}")
    e = _require_decimal("e", e)
    L = _require_decimal("L", L)
    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if L < 0:
        raise ValueError(f"L must be >= 0, got {L}")
    if not position_ecs:
        raise ValueError("position_ecs must be non-empty")
    if REFERENCE_POSITION not in position_ecs:
        raise ValueError(f"position_ecs must include the reference position ({REFERENCE_POSITION})")
    for position_no, value in position_ecs.items():
        if position_no not in TILT_POSITIONS:
            raise ValueError(f"position_no must be one of {TILT_POSITIONS}, got {position_no}")
        _require_decimal("position_ecs value", value)

    mpe_lookup = lookup_mpe(accuracy_class=accuracy_class, m=L / e, e=e, verification_type=verification_type)
    mpe = mpe_lookup.mpe_grams
    reference = position_ecs[REFERENCE_POSITION]
    max_abs_deviation = max(abs(reference - value) for value in position_ecs.values())

    return TiltingLoadedCheckResult(
        L=L, mpe=mpe, mpe_lookup=mpe_lookup, reference_ec=reference,
        max_abs_deviation=max_abs_deviation, within_mpe=max_abs_deviation <= mpe,
    )
