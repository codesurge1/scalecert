"""Pure Eccentricity-test orchestration: no DB, no HTTP — same shape as
app/services/zero_tare.py: the fixed test load is server-derived once, each
position is an independent engine call with its OWN technician-supplied E0.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.contracts.eccentricity import (
    EccentricityReadingIn,
    EccentricityReadingSubmitIn,
    EccentricityResultOut,
    EccentricitySetupOut,
    reading_to_engine_kwargs,
    result_to_out,
)
from app.contracts.instrument import InstrumentParams
from engine.eccentricity import compute_eccentricity_position, generate_eccentricity_load
from engine.mpe import lookup_mpe
from engine.types import VerificationType


def build_load(instrument: InstrumentParams) -> Decimal:
    """The one place generate_eccentricity_load is called from the API
    layer — the single fixed load shared across all 4 positions."""
    return generate_eccentricity_load(max_capacity=instrument.max_capacity)


def setup_out(instrument: InstrumentParams, verification_type: VerificationType) -> EccentricitySetupOut:
    """`GET .../eccentricity/setup`'s response — the one fixed load and its
    mpe, computable before any position has been submitted."""
    L = build_load(instrument)
    e = instrument.e_value
    mpe_lookup = lookup_mpe(accuracy_class=instrument.accuracy_class, m=L / e, e=e, verification_type=verification_type)
    return EccentricitySetupOut(L=L, mpe=mpe_lookup.mpe_grams)


@dataclass(frozen=True)
class SubmissionResult:
    L: Decimal
    reading: EccentricityReadingIn
    result_out: EccentricityResultOut


def compute_result_for_submission(
    submission: EccentricityReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
) -> SubmissionResult:
    L = build_load(instrument)

    reading = EccentricityReadingIn(
        position_no=submission.position_no,
        accuracy_class=instrument.accuracy_class,
        verification_type=verification_type,
        e=instrument.e_value,
        L=L,
        I=submission.I,
        delta_l=submission.delta_l,
        E0=submission.E0,
    )
    engine_kwargs = reading_to_engine_kwargs(reading)
    position_result = compute_eccentricity_position(**engine_kwargs)
    result_out = result_to_out(position_result)

    return SubmissionResult(L=L, reading=reading, result_out=result_out)
