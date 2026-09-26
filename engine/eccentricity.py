"""Eccentricity test — R76-1 A.4.7 / "3.1 weights" (R76-2 page 12, "3
ECCENTRICITY (A.4.7)", "3.1 Eccentricity using weights"). Same change-point
family as Weighing:

  E = I + 1/2*e - deltaL - L
  Ec = E - E0
  PASS iff |Ec| <= mpe

...applied independently at each of 4 receptor positions (1=top-left,
2=top-right, 3=bottom-right, 4=bottom-left, clockwise — the page-12 sketch).
The key structural difference from Weighing: E0 is RE-MEASURED before each
position rather than shared from one session-level zero-capture, so each
position is a fully independent `compute_weighing_result` call with its own
E0 — not a shared baseline subtracted from four readings. Since the
change-point math itself is unchanged, this module is a thin wrapper (same
shape as engine/zero_tare.py), not a reimplementation.

Standard library only — no third-party imports; all arithmetic Decimal.
"""

from decimal import Decimal

from engine.types import AccuracyClass, EccentricityPositionResult, VerificationType
from engine.weighing import compute_weighing_result

# 1=top-left, 2=top-right, 3=bottom-right, 4=bottom-left, clockwise —
# R76-2 page 12's own position sketch.
ECCENTRICITY_POSITIONS = (1, 2, 3, 4)

# The eccentricity test load is a single fixed load applied in turn at each
# of the 4 positions — commonly at least 1/3 of Max (a documented convention
# here, like load_sequence.py's FILL_SPACING_STRATEGY, pending RRSL
# confirmation of an exact figure), never technician-entered. Divides by 3
# directly (rather than pre-multiplying by a rounded Decimal("1")/Decimal("3")
# constant) so an exact case like Max=3000 yields exactly 1000, not a
# 28-digit-precision approximation of 999.999...
_LOAD_DIVISOR = Decimal("3")


def generate_eccentricity_load(*, max_capacity: Decimal) -> Decimal:
    if not isinstance(max_capacity, Decimal):
        raise TypeError(f"max_capacity must be a Decimal, got {type(max_capacity).__name__}")
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")
    return max_capacity / _LOAD_DIVISOR


def compute_eccentricity_position(
    *,
    position_no: int,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    L: Decimal,
    I: Decimal,
    delta_l: Decimal,
    E0: Decimal,
) -> EccentricityPositionResult:
    """One position's full derivation. `E0` is whatever was measured at or
    near zero immediately before THIS position (the caller's
    responsibility, per R76-2 page 12's "E0 ... determined prior to each
    measurement") — never shared with another position's call.
    """
    if position_no not in ECCENTRICITY_POSITIONS:
        raise ValueError(f"position_no must be one of {ECCENTRICITY_POSITIONS}, got {position_no}")

    result = compute_weighing_result(
        accuracy_class=accuracy_class,
        verification_type=verification_type,
        e=e,
        L=L,
        I=I,
        delta_l=delta_l,
        E0=E0,
    )
    return EccentricityPositionResult(position_no=position_no, weighing_result=result)
