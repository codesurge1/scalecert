"""Pure Weighing-test orchestration: no DB, no HTTP — just the generated load
sequence, the submitted reading, and the engine. Kept separate from
routers/repositories specifically so it is unit-testable without a live
Supabase connection (this sandbox has no egress to one; see
backend/tests/services/test_weighing_service.py).
"""

from dataclasses import dataclass

from app.contracts.instrument import InstrumentParams
from app.contracts.weighing import (
    WeighingReadingIn,
    WeighingReadingSubmitIn,
    WeighingResultOut,
    reading_to_engine_kwargs,
    result_to_out,
)
from engine.load_sequence import generate_load_sequence
from engine.types import LoadEntry, VerificationType
from engine.weighing import compute_weighing_result


class SequenceNumberOutOfRange(ValueError):
    """Raised when a requested sequence_no doesn't exist in the load
    sequence generated for this instrument/verification_type."""


def build_sequence(instrument: InstrumentParams, verification_type: VerificationType) -> list[LoadEntry]:
    """The one place `generate_load_sequence` is called from the API layer —
    so `GET .../sequence` and `POST .../readings` can never disagree about
    what sequence_no N means. Deterministic: recomputed on every call rather
    than stored (docs/architecture.md).
    """
    return generate_load_sequence(
        accuracy_class=instrument.accuracy_class,
        e=instrument.e_value,
        max_capacity=instrument.max_capacity,
        min_capacity=instrument.min_capacity,
        verification_type=verification_type,
    )


def load_entry_for_sequence_no(sequence: list[LoadEntry], sequence_no: int) -> LoadEntry:
    if sequence_no < 0 or sequence_no >= len(sequence):
        raise SequenceNumberOutOfRange(
            f"sequence_no {sequence_no} is out of range (0..{len(sequence) - 1})"
        )
    return sequence[sequence_no]


@dataclass(frozen=True)
class SubmissionResult:
    entry: LoadEntry
    reading: WeighingReadingIn
    result_out: WeighingResultOut


def compute_result_for_submission(
    submission: WeighingReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
) -> SubmissionResult:
    """The full pure pipeline for one reading: regenerate the sequence, look
    up L for `submission.sequence_no`, build the engine-ready reading, call
    the engine, adapt the result. Everything here is a plain function of its
    arguments — no DB, no HTTP — so it's unit-testable directly.
    """
    sequence = build_sequence(instrument, verification_type)
    entry = load_entry_for_sequence_no(sequence, submission.sequence_no)

    reading = WeighingReadingIn(
        accuracy_class=instrument.accuracy_class,
        verification_type=verification_type,
        direction=submission.direction,
        e=instrument.e_value,
        L=entry.L,
        I=submission.I,
        delta_l=submission.delta_l,
        E0=submission.E0,
    )
    engine_kwargs = reading_to_engine_kwargs(reading)
    result = compute_weighing_result(**engine_kwargs)
    result_out = result_to_out(result)

    return SubmissionResult(entry=entry, reading=reading, result_out=result_out)
