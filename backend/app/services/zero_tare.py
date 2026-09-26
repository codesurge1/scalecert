"""Pure Zero/tare-test orchestration: no DB, no HTTP — mirrors
app/services/weighing.py's shape exactly (build the check list, look up a
check by sequence_no, run the engine, adapt the result) since the math and
provenance rules (server derives `L`, never the client) are identical.
Unit-testable without a live Supabase connection.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.contracts.instrument import InstrumentParams
from app.contracts.zero_tare import (
    ZeroTareCheckOut,
    ZeroTareReadingIn,
    ZeroTareReadingSubmitIn,
    ZeroTareResultOut,
    reading_to_engine_kwargs,
    result_to_out,
)
from engine.mpe import lookup_mpe
from engine.types import VerificationType
from engine.zero_tare import compute_zero_tare_result, generate_zero_tare_checks


class SequenceNumberOutOfRange(ValueError):
    """Raised when a requested sequence_no doesn't exist in the generated
    zero/tare check list for this instrument."""


def build_checks(instrument: InstrumentParams) -> list[Decimal]:
    """The one place generate_zero_tare_checks is called from the API
    layer — so `GET .../checks` and `POST .../readings` can never disagree
    about what sequence_no N means. Deterministic: recomputed on every
    call, nothing is stored (same convention as Weighing's build_sequence)."""
    return generate_zero_tare_checks(max_capacity=instrument.max_capacity, min_capacity=instrument.min_capacity)


def check_load_for_sequence_no(checks: list[Decimal], sequence_no: int) -> Decimal:
    if sequence_no < 0 or sequence_no >= len(checks):
        raise SequenceNumberOutOfRange(f"sequence_no {sequence_no} is out of range (0..{len(checks) - 1})")
    return checks[sequence_no]


def checks_with_mpe(instrument: InstrumentParams, verification_type: VerificationType) -> list[ZeroTareCheckOut]:
    """`GET .../zero-tare/checks`'s full response — each check load paired
    with its own mpe, so the client knows the mpe before submitting (same
    role as Weighing's `GET .../sequence`)."""
    checks = build_checks(instrument)
    e = instrument.e_value
    out = []
    for sequence_no, L in enumerate(checks):
        mpe_lookup = lookup_mpe(accuracy_class=instrument.accuracy_class, m=L / e, e=e, verification_type=verification_type)
        out.append(ZeroTareCheckOut(sequence_no=sequence_no, L=L, m=L / e, mpe=mpe_lookup.mpe_grams))
    return out


@dataclass(frozen=True)
class SubmissionResult:
    L: Decimal
    reading: ZeroTareReadingIn
    result_out: ZeroTareResultOut


def compute_result_for_submission(
    submission: ZeroTareReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
) -> SubmissionResult:
    checks = build_checks(instrument)
    L = check_load_for_sequence_no(checks, submission.sequence_no)

    reading = ZeroTareReadingIn(
        accuracy_class=instrument.accuracy_class,
        verification_type=verification_type,
        e=instrument.e_value,
        L=L,
        I=submission.I,
        delta_l=submission.delta_l,
        E0=submission.E0,
    )
    engine_kwargs = reading_to_engine_kwargs(reading)
    result = compute_zero_tare_result(**engine_kwargs)
    result_out = result_to_out(result)

    return SubmissionResult(L=L, reading=reading, result_out=result_out)
