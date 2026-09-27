"""Pure Damp heat orchestration (clause 13, B.2): no DB, no HTTP. Mirrors
app/services/weighing.py's shape exactly (regenerate the load sequence,
look up L for a sequence_no, run the SAME engine, adapt the result) — the
math is identical to Weighing; only the run structure (three FIXED,
pre-provisioned runs instead of Weighing's optional technician-labelled
ones) differs, and that lives here as FIXED_RUN_LABELS, not in the engine.
"""

from dataclasses import dataclass

from app.contracts.damp_heat import (
    DampHeatReadingIn,
    DampHeatReadingSubmitIn,
    DampHeatResultOut,
    reading_to_engine_kwargs,
    result_to_out,
)
from app.contracts.instrument import InstrumentParams
from engine.load_sequence import generate_load_sequence
from engine.types import LoadEntry, VerificationType
from engine.weighing import compute_weighing_result

# R76-2 pages 37/38/39's own sub-headings, verbatim — the fixed, known-in-
# advance run structure every Damp heat test has, auto-provisioned by
# POST .../damp-heat/setup rather than technician-labelled like Weighing's
# own optional extra runs.
FIXED_RUN_LABELS = [
    "a) Initial test (at reference temperature)",
    "b) Test at high temperature and 85% relative humidity",
    "c) Final test (at reference temperature)",
]


class SequenceNumberOutOfRange(ValueError):
    """Raised when a requested sequence_no doesn't exist in the load
    sequence generated for this instrument/verification_type."""


def build_sequence(instrument: InstrumentParams, verification_type: VerificationType) -> list[LoadEntry]:
    """The one place `generate_load_sequence` is called for Damp heat — so
    `GET .../sequence` and `POST .../readings` can never disagree about
    what sequence_no N means. Deterministic: recomputed on every call
    (same convention as Weighing's own build_sequence), never stored."""
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
    reading: DampHeatReadingIn
    result_out: DampHeatResultOut


def compute_result_for_submission(
    submission: DampHeatReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
) -> SubmissionResult:
    """The full pure pipeline for one Damp heat reading — identical shape
    to weighing_service.compute_result_for_submission, calling the exact
    same engine function (compute_weighing_result); only the contract
    types differ."""
    sequence = build_sequence(instrument, verification_type)
    entry = load_entry_for_sequence_no(sequence, submission.sequence_no)

    reading = DampHeatReadingIn(
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
