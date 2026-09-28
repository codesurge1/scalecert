"""Cross-run comparison (feat/test-runs-conditions): the shared math behind
every OIML test that is the SAME procedure re-run under different
conditions, where the test IS the comparison between runs — clause 1
Weighing at multiple temperatures (page 9), clause 13 Damp heat (initial /
high-temp+humidity / final), clause 15 Endurance (initial / after N cycles
/ final). Weighing is the first consumer of this module; Damp heat and
Endurance are not built by this task, but this function is written generic
enough that either can call it unmodified when they are (docs/architecture.md).

variation_error = |Ec_a - Ec_b|, PASS iff variation_error <= mpe (limit
inclusive — same convention as engine.weighing.compute_weighing_result).
The order of the two runs never matters: the error is a magnitude, not a
directional delta, so compute_run_comparison(Ec_a=x, Ec_b=y, ...) and
compute_run_comparison(Ec_a=y, Ec_b=x, ...) always agree.

`compute_durability_check` (added `feat/damp-heat-endurance`) is
Endurance's own aggregate on top of the same per-load comparisons: EVERY
load's durability error must be within mpe, not just some.

All arithmetic is Decimal, never float. Every input is required and
type-checked explicitly — no default values. Standard library only.
"""

from decimal import Decimal
from typing import Iterable

from engine.types import DurabilityCheckResult, RunComparisonResult


def _require_decimal(name: str, value) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    return value


def compute_run_comparison(*, Ec_a: Decimal, Ec_b: Decimal, mpe: Decimal) -> RunComparisonResult:
    """Compare two runs' corrected error (Ec) for the SAME load.

    `Ec_a`/`Ec_b` are the two runs' own corrected error (e.g.
    `WeighingResult.Ec`) at one load; `mpe` is that load's own limit. The
    two runs should share the same mpe (same load/class/verification_type)
    — the caller decides which run's mpe to pass in, since this function
    has no way to re-derive or cross-check it itself.
    """
    Ec_a = _require_decimal("Ec_a", Ec_a)
    Ec_b = _require_decimal("Ec_b", Ec_b)
    mpe = _require_decimal("mpe", mpe)

    if mpe < 0:
        raise ValueError(f"mpe must be >= 0, got {mpe}")

    variation_error = abs(Ec_a - Ec_b)
    margin = mpe - variation_error
    passed = variation_error <= mpe

    return RunComparisonResult(
        Ec_a=Ec_a,
        Ec_b=Ec_b,
        variation_error=variation_error,
        mpe=mpe,
        margin=margin,
        passed=passed,
    )


def compute_durability_check(comparisons: Iterable[RunComparisonResult]) -> DurabilityCheckResult:
    """Endurance's own aggregate verdict rule (R76-1 A.6, R76-2 page 47):
    the durability error due to wear and tear must be `<= mpe` for EVERY
    load, not just some — a genuinely different aggregation from a single
    `compute_run_comparison` call, the same "whole-set property, not a
    single reading" shape as `engine.repeatability.compute_repeatability_series`
    (spread across a whole series) and `engine.tilting.compute_tilting_loaded_check`
    (max deviation across positions).

    An EMPTY `comparisons` (no matching loads submitted in both runs yet)
    is never trusted as a pass — `all_passed` is `False` until there is at
    least one comparison, mirroring `passed` always starting `False` in
    every other "nothing submitted yet" state in this app.
    """
    comparisons = tuple(comparisons)
    for index, comparison in enumerate(comparisons):
        if not isinstance(comparison, RunComparisonResult):
            raise TypeError(f"comparisons[{index}] must be a RunComparisonResult, got {type(comparison).__name__}")

    all_passed = bool(comparisons) and all(comparison.passed for comparison in comparisons)
    return DurabilityCheckResult(comparisons=comparisons, all_passed=all_passed)
