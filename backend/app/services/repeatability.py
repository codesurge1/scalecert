"""Pure Repeatability-test orchestration: no DB, no HTTP.

Unlike Weighing/Zero-tare, a series' verdict is a property of the WHOLE set
of readings submitted so far (the spread criterion), not any single one —
so there is one function, `compute_series`, that both the readings-POST
route (recompute the up-to-date series state after inserting a new reading)
and the readings-GET route (recompute the current series state on load) call
identically. This keeps a single source of truth for "what does series N
look like right now" rather than two slightly different code paths.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence, Tuple

from app.contracts.instrument import InstrumentParams
from app.contracts.repeatability import RepeatabilityReadingSubmitIn, RepeatabilitySeriesOut, series_result_to_out
from engine.mpe import lookup_mpe
from engine.repeatability import compute_repeatability_series, generate_repeatability_load
from engine.types import VerificationType


def build_series_load(instrument: InstrumentParams, series_no: int) -> Decimal:
    """The one place generate_repeatability_load is called from the API
    layer, so every caller agrees on what series_no 1/2 means."""
    return generate_repeatability_load(series_no=series_no, max_capacity=instrument.max_capacity)


def series_mpe(instrument: InstrumentParams, verification_type: VerificationType, series_no: int) -> Decimal:
    """The mpe for a series, computable even with zero readings submitted
    yet (needed so `GET .../readings` can show L/mpe for a not-yet-started
    series) — reuses generate_repeatability_load + engine.mpe.lookup_mpe
    directly rather than requiring at least one reading, unlike
    compute_repeatability_series itself."""
    L = build_series_load(instrument, series_no)
    e = instrument.e_value
    return lookup_mpe(accuracy_class=instrument.accuracy_class, m=L / e, e=e, verification_type=verification_type).mpe_grams


def compute_series(
    instrument: InstrumentParams,
    verification_type: VerificationType,
    series_no: int,
    stored_readings: Sequence[Tuple[int, Decimal, Decimal]],
) -> RepeatabilitySeriesOut:
    """`stored_readings`: (sequence_no, I, delta_l) tuples, any order, one
    per DISTINCT sequence_no already deduped by the caller (a resubmitted
    sequence_no is a second insert — see app/repositories/readings.py — so
    the caller is responsible for last-write-wins dedup before this point,
    the same way Weighing's readings-list route already does). Returns a
    series with empty `readings`/None aggregate fields if `stored_readings`
    is empty — "not started yet" is a legitimate state, not an error, even
    though the pure engine function itself requires a non-empty set.
    """
    L = build_series_load(instrument, series_no)

    if not stored_readings:
        return RepeatabilitySeriesOut(
            series_no=series_no,
            L=L,
            mpe=series_mpe(instrument, verification_type, series_no),
            readings=[],
        )

    sorted_readings = sorted(stored_readings, key=lambda r: r[0])
    sequence_nos = [r[0] for r in sorted_readings]
    pairs = [(r[1], r[2]) for r in sorted_readings]

    result = compute_repeatability_series(
        accuracy_class=instrument.accuracy_class,
        verification_type=verification_type,
        e=instrument.e_value,
        series_no=series_no,
        L=L,
        readings=pairs,
    )
    return series_result_to_out(result, sequence_nos)


@dataclass(frozen=True)
class SubmissionResult:
    series_out: RepeatabilitySeriesOut
    """The up-to-date state of the WHOLE series (including the just-submitted
    reading), not just that one reading — the response a client needs to
    show live spread/mpe/pass-fail after every submission."""

    this_reading_within_mpe: bool
    """This specific submission's own |E| <= mpe — what gets stored as
    `test_results.passed` for its own reading_id row."""

    this_reading_E: Decimal


def compute_result_for_submission(
    submission: RepeatabilityReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
    existing_readings: Sequence[Tuple[int, Decimal, Decimal]],
) -> SubmissionResult:
    """`existing_readings`: this series' already-stored (sequence_no, I,
    delta_l) tuples, BEFORE this submission — last-write-wins merged with
    the new one (same sequence_no overwrites, matching the "resubmission is
    a second insert, dedup to latest" convention). Recomputes the whole
    series (see compute_series) rather than trying to patch a stored
    aggregate incrementally.
    """
    merged = {sequence_no: (I, delta_l) for sequence_no, I, delta_l in existing_readings}
    merged[submission.sequence_no] = (submission.I, submission.delta_l)
    stored_readings = [(sequence_no, I, delta_l) for sequence_no, (I, delta_l) in merged.items()]

    series_out = compute_series(instrument, verification_type, submission.series_no, stored_readings)

    this_reading = next(r for r in series_out.readings if r.sequence_no == submission.sequence_no)
    return SubmissionResult(
        series_out=series_out,
        this_reading_within_mpe=this_reading.within_mpe,
        this_reading_E=this_reading.E,
    )
