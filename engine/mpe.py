"""MPE lookup — OIML R76-1 Table 6 (initial verification bands).

Inputs: accuracy class, load in multiples of e (m), the scale interval e itself
(needed only to convert the looked-up mpe-in-e figure to grams), and the
verification type. `initial` and `subsequent` use the Table 6 values as written;
`in_service` doubles them (clause 3.5.2 / 8.4.2).

Band edges are exact: the upper bound of each row is inclusive, the lower bound
of the next row is exclusive of it (e.g. Class III: m=500 -> 0.5e, m=501 -> 1.0e).
Standard library only — no third-party imports.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from engine.types import AccuracyClass, MpeResult, VerificationType

# Each row: (upper_bound_m_inclusive, mpe_in_e). `None` upper bound means unbounded above.
_Band = Tuple[Optional[Decimal], Decimal]

BAND_TABLE: Dict[AccuracyClass, List[_Band]] = {
    AccuracyClass.I: [
        (Decimal("50000"), Decimal("0.5")),
        (Decimal("200000"), Decimal("1.0")),
        (None, Decimal("1.5")),
    ],
    AccuracyClass.II: [
        (Decimal("5000"), Decimal("0.5")),
        (Decimal("20000"), Decimal("1.0")),
        (Decimal("100000"), Decimal("1.5")),
    ],
    AccuracyClass.III: [
        (Decimal("500"), Decimal("0.5")),
        (Decimal("2000"), Decimal("1.0")),
        (Decimal("10000"), Decimal("1.5")),
    ],
    AccuracyClass.IIII: [
        (Decimal("50"), Decimal("0.5")),
        (Decimal("200"), Decimal("1.0")),
        (Decimal("1000"), Decimal("1.5")),
    ],
}

IN_SERVICE_MULTIPLIER = Decimal("2")


def lookup_mpe(
    *,
    accuracy_class: AccuracyClass,
    m: Decimal,
    e: Decimal,
    verification_type: VerificationType,
) -> MpeResult:
    """Look up the MPE for a load of `m` multiples of `e`. No silent defaults:
    every argument is required and type-checked explicitly."""
    if not isinstance(accuracy_class, AccuracyClass):
        raise TypeError(f"accuracy_class must be an AccuracyClass, got {type(accuracy_class).__name__}")
    if not isinstance(verification_type, VerificationType):
        raise TypeError(f"verification_type must be a VerificationType, got {type(verification_type).__name__}")
    if not isinstance(m, Decimal):
        raise TypeError(f"m must be a Decimal, got {type(m).__name__}")
    if not isinstance(e, Decimal):
        raise TypeError(f"e must be a Decimal, got {type(e).__name__}")
    if m < 0:
        raise ValueError(f"m must be >= 0, got {m}")
    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")

    bands = BAND_TABLE[accuracy_class]
    lower = Decimal("0")
    band_upper: Optional[Decimal] = None
    mpe_in_e: Optional[Decimal] = None
    for upper, candidate in bands:
        if upper is None or m <= upper:
            band_upper = upper
            mpe_in_e = candidate
            break
        lower = upper
    else:
        raise ValueError(
            f"m={m} is outside the defined Table 6 range for class {accuracy_class.value}"
        )

    if verification_type is VerificationType.IN_SERVICE:
        mpe_in_e = mpe_in_e * IN_SERVICE_MULTIPLIER

    mpe_grams = mpe_in_e * e

    return MpeResult(
        accuracy_class=accuracy_class,
        verification_type=verification_type,
        e=e,
        m=m,
        mpe_in_e=mpe_in_e,
        mpe_grams=mpe_grams,
        band_lower_m=lower,
        band_upper_m=band_upper,
    )
