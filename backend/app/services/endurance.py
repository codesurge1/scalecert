"""Pure Endurance orchestration (clause 15, A.6): no DB, no HTTP. Mirrors
app/services/weighing.py's shape exactly for the a)/c) Weighing-formula
runs; the b) cycling step has no computation at all (R76-2 page 47 just
records "Number of loadings"/"Load applied") so there is no function for
it here — the router writes it straight to the Final run's `conditions`
via app.repositories.runs.update_run_conditions.
"""

from dataclasses import dataclass

from app.contracts.endurance import (
    EnduranceReadingIn,
    EnduranceReadingSubmitIn,
    EnduranceResultOut,
    reading_to_engine_kwargs,
    result_to_out,
)
from app.contracts.instrument import InstrumentParams
from engine.load_sequence import generate_load_sequence
from engine.types import LoadEntry, VerificationType
from engine.weighing import compute_weighing_result

# R76-2 pages 46/47's own sub-headings — the fixed, known-in-advance run
# structure every Endurance test has (just two: no equivalent of Damp
# heat's middle "b" run, since Endurance's own "b) Performance of the
# test" is a non-computed cycling step, not a third Weighing run).
FIXED_RUN_LABELS = [
    "a) Initial test",
    "c) Final test",
]

# The Final run's fixed label — the one `test_runs` row Endurance's
# cycling step (loadings/load applied) is recorded on (ADR-0011).
FINAL_RUN_LABEL = FIXED_RUN_LABELS[1]


class SequenceNumberOutOfRange(ValueError):
    """Raised when a requested sequence_no doesn't exist in the load
    sequence generated for this instrument/verification_type."""


def build_sequence(instrument: InstrumentParams, verification_type: VerificationType) -> list[LoadEntry]:
    """The one place `generate_load_sequence` is called for Endurance —
    deterministic, recomputed on every call, never stored (same
    convention as Weighing's own build_sequence)."""
    return generate_load_sequence(
        accuracy_class=instrument.accuracy_class,
        e=instrument.e_value,
        max_capacity=instrument.max_capacity,
        min_capacity=instrument.min_capacity,
        verification_type=verification_type,
    )


def load_entry_for_sequence_no(sequence: list[LoadEntry], sequence_no: int) -> LoadEntry:
    if sequence_no < 0 or sequence_no >= len(sequence):
        raise SequenceNumberOutOfRange(f"sequence_no {sequence_no} is out of range (0..{len(sequence) - 1})")
    return sequence[sequence_no]


@dataclass(frozen=True)
class SubmissionResult:
    entry: LoadEntry
    reading: EnduranceReadingIn
    result_out: EnduranceResultOut


def compute_result_for_submission(
    submission: EnduranceReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
) -> SubmissionResult:
    """The full pure pipeline for one Endurance a)/c) reading — identical
    shape to weighing_service.compute_result_for_submission, calling the
    exact same engine function (compute_weighing_result); only the
    contract types differ."""
    sequence = build_sequence(instrument, verification_type)
    entry = load_entry_for_sequence_no(sequence, submission.sequence_no)

    reading = EnduranceReadingIn(
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
