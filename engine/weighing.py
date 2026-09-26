"""Weighing test (R76-1 A.4.4-A.4.6) change-point calculation and verdict.

E = I + 1/2*e - deltaL - L
Ec = E - E0
PASS iff |Ec| <= mpe (mpe from the Table 6 lookup for this class/load-band/
verification-type).

All arithmetic is Decimal, never float — a boundary case must not turn on
floating-point rounding. No silent defaults: every input is required and
type-checked explicitly; a missing or wrong-typed input raises, it is never
guessed. Standard library only — no third-party imports.
"""

from decimal import Decimal

from engine.mpe import lookup_mpe
from engine.types import AccuracyClass, VerificationType, WeighingResult

HALF = Decimal("0.5")


def _require_decimal(name: str, value) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    return value


def compute_weighing_result(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    L: Decimal,
    I: Decimal,
    delta_l: Decimal,
    E0: Decimal,
) -> WeighingResult:
    """Compute the full Weighing-test derivation for one reading.

    L is the auto-generated applied load; I and delta_l (additional load) are
    what the technician actually enters. E0 is the error at/near zero. Every
    argument is required — there is no default for any of them.
    """
    if not isinstance(accuracy_class, AccuracyClass):
        raise TypeError(f"accuracy_class must be an AccuracyClass, got {type(accuracy_class).__name__}")
    if not isinstance(verification_type, VerificationType):
        raise TypeError(f"verification_type must be a VerificationType, got {type(verification_type).__name__}")

    e = _require_decimal("e", e)
    L = _require_decimal("L", L)
    I = _require_decimal("I", I)
    delta_l = _require_decimal("delta_l", delta_l)
    E0 = _require_decimal("E0", E0)

    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if L < 0:
        raise ValueError(f"L must be >= 0, got {L}")

    m = L / e
    mpe_lookup = lookup_mpe(
        accuracy_class=accuracy_class,
        m=m,
        e=e,
        verification_type=verification_type,
    )

    E = I + HALF * e - delta_l - L
    Ec = E - E0
    mpe = mpe_lookup.mpe_grams
    margin = mpe - abs(Ec)
    passed = abs(Ec) <= mpe

    return WeighingResult(
        accuracy_class=accuracy_class,
        verification_type=verification_type,
        e=e,
        L=L,
        I=I,
        delta_l=delta_l,
        E0=E0,
        E=E,
        Ec=Ec,
        mpe=mpe,
        margin=margin,
        passed=passed,
        mpe_lookup=mpe_lookup,
    )
