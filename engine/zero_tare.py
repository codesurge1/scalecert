"""Zero/tare device accuracy test — R76-1 A.4.4's zero/tare-device variant of
the Weighing test (docs/plan.md; the OIML checklist item "Weighing (incl.
zero/tare device accuracy)"). Same change-point family as Weighing:

  E = I + 1/2*e - deltaL - L
  Ec = E - E0
  PASS iff |Ec| <= mpe

Modeled as a thin wrapper around `engine.weighing.compute_weighing_result`
rather than a duplicate implementation — the zero/tare device check IS the
Weighing formula applied to a handful of small check loads near the low end
of the range, not a different formula. Kept as its own named entry point
(not a bare re-export) so the contract/service layer has a stable,
test-specific seam to call, and so a future divergence (if RRSL ever
specifies zero/tare-specific math) has somewhere to live without touching
engine/weighing.py.

Unlike the full Weighing test, there is no auto-generated Table-6-anchored
load sequence here — a zero/tare check is "a few readings on the zero/tare
device," not a full-range verification. `generate_zero_tare_checks` produces
a small, deterministic, reproducible set of check loads instead: the zero
point itself, plus two more small loads near the low end of the range, so
the technician still never invents/enters `L` directly (same "server
derives it" discipline as the rest of the app), even though there's no
Table 6 band structure to anchor to here.
"""

from decimal import Decimal
from typing import Optional

from engine.types import AccuracyClass, VerificationType, WeighingResult
from engine.weighing import compute_weighing_result

ZERO_TARE_CHECK_COUNT = 3

# When no min_capacity is known, the low-end anchor for the second and third
# check loads falls back to this fraction of Max — a documented convention
# (like load_sequence.py's FILL_SPACING_STRATEGY), not an OIML-sourced
# figure, pending RRSL confirmation of an actual zero/tare check-load
# convention.
_FALLBACK_ANCHOR_FRACTION_OF_MAX = Decimal("0.05")


def generate_zero_tare_checks(
    *, max_capacity: Decimal, min_capacity: Optional[Decimal]
) -> list[Decimal]:
    """Three fixed, deterministic check loads: 0 (the zero point itself),
    and two more small loads near the low end of the range where a
    zero/tare device is actually exercised. Uses `min_capacity` as the
    anchor for the low-end loads when it's known (it's the smallest load the
    instrument is meant to weigh accurately, a natural zero/tare-relevant
    figure); otherwise falls back to a small fraction of Max.
    """
    if not isinstance(max_capacity, Decimal):
        raise TypeError(f"max_capacity must be a Decimal, got {type(max_capacity).__name__}")
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")
    if min_capacity is not None:
        if not isinstance(min_capacity, Decimal):
            raise TypeError(f"min_capacity must be a Decimal or None, got {type(min_capacity).__name__}")
        if min_capacity < 0:
            raise ValueError(f"min_capacity must be >= 0, got {min_capacity}")

    anchor = min_capacity if (min_capacity is not None and min_capacity > 0) else max_capacity * _FALLBACK_ANCHOR_FRACTION_OF_MAX
    return [Decimal("0"), anchor, anchor * 2]


def compute_zero_tare_result(
    *,
    accuracy_class: AccuracyClass,
    verification_type: VerificationType,
    e: Decimal,
    L: Decimal,
    I: Decimal,
    delta_l: Decimal,
    E0: Decimal,
) -> WeighingResult:
    """Identical arguments and return shape to compute_weighing_result — see
    module docstring for why this delegates rather than reimplementing."""
    return compute_weighing_result(
        accuracy_class=accuracy_class,
        verification_type=verification_type,
        e=e,
        L=L,
        I=I,
        delta_l=delta_l,
        E0=E0,
    )
