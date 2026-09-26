"""Accuracy-class derivation — OIML R76-1 Table 3 (clause 3.4, "Classes of
NAWIs": verification scale interval e, number of verification scale
intervals n = Max/e, and minimum capacity Min, each as a function of class).

Accuracy class is NEVER chosen by the person registering an instrument — it
is derived here, purely, from the instrument's own physical parameters (e,
Max, Min), the same way the Weighing load sequence is server-derived from
the instrument rather than technician-entered (CLAUDE.md). An instrument
whose e/Max/Min fit no class at all is invalid and must be rejected at
registration, not silently accepted with a class the numbers don't actually
support — that gap is exactly what previously let an instrument get
registered as "Class III" with n=15000 (exceeding Class III's own n_max of
10000, per Table 3 below) and later crash the Weighing load-sequence
endpoint: engine.load_sequence and engine.mpe.lookup_mpe both trust the
stored class's Table 6 band range and never re-derive or re-validate it
against Table 3 themselves — that isn't their job, this module's is.

Table 3 data, and its relationship to engine.mpe.BAND_TABLE (Table 6): each
class's n_max here is EXACTLY the upper bound of that class's last Table 6
MPE band — Table 6 only needs to define bands up to where the class itself
stops applying, so n_max is read directly from BAND_TABLE (`_n_max_for_class`
below) rather than kept as a second hardcoded copy that could silently
drift out of sync with it.

Single-interval instruments only, same limitation as engine/load_sequence.py
— multi-interval classification (per-sub-range e/n/Min) is a known future
extension, not handled here.

Standard library only — no third-party imports (same purity guardrail as
the rest of engine/).
"""

from decimal import Decimal
from typing import List, Optional

from engine.mpe import BAND_TABLE
from engine.types import AccuracyClass, ClassificationResult


def _n_max_for_class(accuracy_class: AccuracyClass) -> Optional[Decimal]:
    """Table 3's n_max for a class == the upper bound of that class's last
    Table 6 MPE band (engine.mpe.BAND_TABLE) — see module docstring. `None`
    means unbounded above (Class I only)."""
    return BAND_TABLE[accuracy_class][-1][0]


class _ClassRow:
    """One row of Table 3: a (class, e-range) combination with its own
    n-range and its Min-capacity requirement (as a multiple of e). Classes
    II and III each have two rows — a lower-e and a higher-e range with
    different n_min/Min requirements — so this is a list of rows, not a
    dict keyed by class.
    """

    __slots__ = ("accuracy_class", "e_min", "e_max", "n_min", "n_max", "min_multiple_of_e")

    def __init__(
        self,
        accuracy_class: AccuracyClass,
        *,
        e_min: Decimal,
        e_max: Optional[Decimal],
        n_min: Decimal,
        min_multiple_of_e: Decimal,
    ) -> None:
        self.accuracy_class = accuracy_class
        self.e_min = e_min
        self.e_max = e_max
        self.n_min = n_min
        self.n_max = _n_max_for_class(accuracy_class)
        self.min_multiple_of_e = min_multiple_of_e

    def e_in_range(self, e: Decimal) -> bool:
        if e < self.e_min:
            return False
        if self.e_max is not None and e > self.e_max:
            return False
        return True

    def n_in_range(self, n: Decimal) -> bool:
        if n < self.n_min:
            return False
        if self.n_max is not None and n > self.n_max:
            return False
        return True


# OIML R76-1 Table 3, verbatim per row (e bounds in grams; both bounds
# inclusive where given).
TABLE_3: List[_ClassRow] = [
    _ClassRow(
        AccuracyClass.I,
        e_min=Decimal("0.001"), e_max=None,
        n_min=Decimal("50000"), min_multiple_of_e=Decimal("100"),
    ),
    _ClassRow(
        AccuracyClass.II,
        e_min=Decimal("0.001"), e_max=Decimal("0.05"),
        n_min=Decimal("100"), min_multiple_of_e=Decimal("20"),
    ),
    _ClassRow(
        AccuracyClass.II,
        e_min=Decimal("0.1"), e_max=None,
        n_min=Decimal("5000"), min_multiple_of_e=Decimal("50"),
    ),
    _ClassRow(
        AccuracyClass.III,
        e_min=Decimal("0.1"), e_max=Decimal("2"),
        n_min=Decimal("100"), min_multiple_of_e=Decimal("20"),
    ),
    _ClassRow(
        AccuracyClass.III,
        e_min=Decimal("5"), e_max=None,
        n_min=Decimal("500"), min_multiple_of_e=Decimal("20"),
    ),
    _ClassRow(
        AccuracyClass.IIII,
        e_min=Decimal("5"), e_max=None,
        n_min=Decimal("100"), min_multiple_of_e=Decimal("10"),
    ),
]

# clause 3.4.2: e must be 1, 2, or 5 x 10^k grams (the standard 1-2-5
# verification-scale-interval sequence), not an arbitrary decimal value.
_VALID_E_SIGNIFICANDS = (Decimal("1"), Decimal("2"), Decimal("5"))


def _is_valid_e(e: Decimal) -> bool:
    """True iff e = m x 10^k for m in {1, 2, 5}. Uses Decimal.normalize()'s
    digit tuple — exact, no float/log-based rounding risk. normalize()
    strips trailing zeros, so a 1/2/5 x 10^k value always normalizes to a
    single significant digit (e.g. Decimal("0.050") -> digits (5,), exponent
    -2, i.e. 5 x 10^-2)."""
    if e <= 0:
        return False
    digits = e.normalize().as_tuple().digits
    return len(digits) == 1 and Decimal(digits[0]) in _VALID_E_SIGNIFICANDS


def _require_decimal(name: str, value) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    return value


def classify_instrument(
    *,
    e: Decimal,
    max_capacity: Decimal,
    min_capacity: Decimal,
    d: Optional[Decimal] = None,
) -> ClassificationResult:
    """Derive the OIML R76-1 Table 3 accuracy class(es) an instrument
    qualifies for, from its own e/Max/Min — never technician-chosen.

    `min_capacity` is REQUIRED here — unlike engine.load_sequence's
    `min_capacity`, which is optional for a different reason entirely
    (whether Min is tested as a verification anchor, not whether it's
    known). Every Table 3 row carries a Min-capacity requirement, so
    classification cannot be performed at all without it.

    `d`, if given, is checked against clause 3.4.2's `d < e <= 10d`
    relationship (this is a different check from `e`'s own 1/2/5 x 10^k
    validity, which always runs regardless of whether `d` is given).

    Returns a ClassificationResult with `n` (= max_capacity / e) always
    populated — useful in a rejection message even on failure —
    `qualified_classes` (zero, one, or more; the caller decides what "more
    than one" means for their purpose, e.g. registration requires the
    client to pick among them), and `reason` populated whenever
    `qualified_classes` is empty, naming exactly which constraint(s) failed.

    Argument type/domain errors (not a Decimal; e/max_capacity <= 0;
    min_capacity < 0) raise TypeError/ValueError immediately — those are
    caller bugs, not legitimate "this instrument doesn't fit any class"
    outcomes, which is what the returned result's `reason` is for.
    """
    e = _require_decimal("e", e)
    max_capacity = _require_decimal("max_capacity", max_capacity)
    min_capacity = _require_decimal("min_capacity", min_capacity)
    if d is not None:
        d = _require_decimal("d", d)

    if e <= 0:
        raise ValueError(f"e must be > 0, got {e}")
    if max_capacity <= 0:
        raise ValueError(f"max_capacity must be > 0, got {max_capacity}")
    if min_capacity < 0:
        raise ValueError(f"min_capacity must be >= 0, got {min_capacity}")

    n = max_capacity / e

    if not _is_valid_e(e):
        return ClassificationResult(
            n=n,
            qualified_classes=(),
            reason=(
                f"e={e}g is not a valid verification scale interval — clause 3.4.2 requires "
                f"e = 1, 2, or 5 x 10^k grams (e.g. 0.1, 0.2, 0.5, 1, 2, 5, 10, ...)."
            ),
        )

    if d is not None and not (d < e <= 10 * d):
        return ClassificationResult(
            n=n,
            qualified_classes=(),
            reason=(
                f"d={d}g and e={e}g do not satisfy clause 3.4.2's d < e <= 10d "
                f"(e/d ratio = {e / d})."
            ),
        )

    applicable_rows = [row for row in TABLE_3 if row.e_in_range(e)]
    if not applicable_rows:
        return ClassificationResult(
            n=n,
            qualified_classes=(),
            reason=f"No Table 3 accuracy class defines a range for e={e}g.",
        )

    qualified: List[AccuracyClass] = []
    failures: List[str] = []
    for row in applicable_rows:
        min_required = row.min_multiple_of_e * e
        n_ok = row.n_in_range(n)
        min_ok = min_capacity >= min_required

        if n_ok and min_ok:
            if row.accuracy_class not in qualified:
                qualified.append(row.accuracy_class)
            continue

        if not n_ok:
            exceeds_max = row.n_max is not None and n > row.n_max
            bound_word = "maximum" if exceeds_max else "minimum"
            bound_value = row.n_max if exceeds_max else row.n_min
            failures.append(
                f"Class {row.accuracy_class.value} requires n between {row.n_min} and "
                f"{row.n_max if row.n_max is not None else 'unbounded'} "
                f"(got n={n}, {'exceeds' if exceeds_max else 'is below'} the {bound_word} of {bound_value})"
            )
        if not min_ok:
            failures.append(
                f"Class {row.accuracy_class.value} requires Min >= {row.min_multiple_of_e}e = "
                f"{min_required}g (got Min={min_capacity}g)"
            )

    if qualified:
        return ClassificationResult(n=n, qualified_classes=tuple(qualified), reason=None)

    reason = (
        f"No accuracy class fits e={e}g, Max={max_capacity}g (n={n}), Min={min_capacity}g: "
        + "; ".join(failures) + "."
    )
    return ClassificationResult(n=n, qualified_classes=(), reason=reason)
