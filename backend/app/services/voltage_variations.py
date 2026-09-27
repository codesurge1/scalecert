"""Pure Voltage-variations orchestration (clause 11, A.5.4): no DB, no
HTTP. Reuses engine.weighing.compute_weighing_result directly — see
app/contracts/voltage_variations.py's module docstring for why this is a
Weighing-formula application, not a new engine.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.contracts.instrument import InstrumentParams
from app.contracts.voltage_variations import (
    VOLTAGE_LEVEL_LABELS,
    VOLTAGE_LEVELS,
    VoltageVariationsLevelOut,
    VoltageVariationsReadingSubmitIn,
    VoltageVariationsResultOut,
)
from engine.mpe import lookup_mpe
from engine.types import VerificationType
from engine.weighing import compute_weighing_result

TEN = Decimal("10")


class UnknownLevelKey(ValueError):
    """Raised when a submitted level_key isn't one of the three fixed
    voltage levels (defensive — Pydantic's Literal already rejects this at
    the contract layer, but the service stays self-contained)."""


def load_for(instrument: InstrumentParams) -> Decimal:
    """The single fixed load this test is always run at — 10 e, the exact
    figure printed on the form ("10 e =") — server-derived, never
    technician-entered."""
    return instrument.e_value * TEN


def level_index(level_key: str) -> int:
    try:
        return VOLTAGE_LEVELS.index(level_key)
    except ValueError as exc:
        raise UnknownLevelKey(f"{level_key!r} is not one of {VOLTAGE_LEVELS}") from exc


def levels_with_mpe(instrument: InstrumentParams, verification_type: VerificationType) -> list[VoltageVariationsLevelOut]:
    """`GET .../voltage-variations/levels`'s full response — the same 10e
    load and its mpe at each of the three levels (the mpe band only depends
    on the load/class/verification_type, not the voltage itself, so it's
    identical across all three — still returned per-level for a uniform
    client shape, same convention as Sensitivity's checks_with_mpe)."""
    L = load_for(instrument)
    e = instrument.e_value
    mpe_lookup = lookup_mpe(accuracy_class=instrument.accuracy_class, m=L / e, e=e, verification_type=verification_type)
    return [
        VoltageVariationsLevelOut(level_key=level_key, label=VOLTAGE_LEVEL_LABELS[level_key], L=L, mpe=mpe_lookup.mpe_grams)
        for level_key in VOLTAGE_LEVELS
    ]


@dataclass(frozen=True)
class SubmissionResult:
    L: Decimal
    result_out: VoltageVariationsResultOut


def compute_result_for_submission(
    submission: VoltageVariationsReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
) -> SubmissionResult:
    level_index(submission.level_key)  # validates; raises UnknownLevelKey if not one of the three
    L = load_for(instrument)

    result = compute_weighing_result(
        accuracy_class=instrument.accuracy_class,
        verification_type=verification_type,
        e=instrument.e_value,
        L=L,
        I=submission.I,
        delta_l=submission.delta_l,
        E0=submission.E0,
    )
    result_out = VoltageVariationsResultOut(
        level_key=submission.level_key,
        U=submission.U,
        L=result.L,
        I=result.I,
        delta_l=result.delta_l,
        E0=result.E0,
        E=result.E,
        Ec=result.Ec,
        mpe=result.mpe,
        passed=result.passed,
    )
    return SubmissionResult(L=L, result_out=result_out)
