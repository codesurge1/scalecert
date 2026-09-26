"""Pydantic v2 contracts for the Repeatability test (R76-1 A.4.5/A.4.10,
engine/repeatability.py) — structurally different from Weighing: no
`direction`, no `E0`/`Ec`, and a reading is identified by (series_no,
sequence_no) rather than direction. A series' pass/fail is a property of the
WHOLE series (the spread criterion), not any single reading, so
`RepeatabilitySeriesOut` — not a per-reading result — is this module's
primary output shape.
"""

from typing import Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal
from engine.types import RepeatabilitySeriesResult


class RepeatabilityReadingSubmitIn(BaseModel):
    """What the client POSTs for one Repeatability reading. No `L` (server-
    derived per series from engine.repeatability.generate_repeatability_load,
    never technician-entered) and no `E0`/`direction` — this test has
    neither (see module docstring)."""

    model_config = ConfigDict(extra="forbid")

    series_no: int = Field(ge=1, le=2, description="1 (~50% of Max) or 2 (~100% of Max, R76-1 A.4.5).")
    sequence_no: int = Field(ge=0, le=9, description="Index within the series — 10 readings per series.")
    I: StrictDecimal
    delta_l: StrictDecimal


class RepeatabilityReadingRecordOut(BaseModel):
    """One reading within a series — I/delta_l as submitted, plus the
    computed E and whether it individually falls within the series' mpe."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    I: StrictDecimal
    delta_l: StrictDecimal
    E: StrictDecimal
    within_mpe: bool


class RepeatabilitySeriesOut(BaseModel):
    """The full state of one Repeatability series — L and mpe are always
    known (server-derived from the instrument, independent of how many
    readings have been submitted); the aggregate fields
    (e_max/e_min/spread/all_within_mpe/spread_within_mpe/passed) are
    Optional and only populated once at least one reading exists, since
    `engine.repeatability.compute_repeatability_series` requires a
    non-empty reading set (a spread needs at least one value to be
    meaningful) — an empty series is a legitimate "not started yet" state,
    not an error.
    """

    model_config = ConfigDict(extra="forbid")

    series_no: int
    L: StrictDecimal
    mpe: StrictDecimal
    readings: list[RepeatabilityReadingRecordOut] = []
    e_max: Optional[StrictDecimal] = None
    e_min: Optional[StrictDecimal] = None
    spread: Optional[StrictDecimal] = None
    all_within_mpe: Optional[bool] = None
    spread_within_mpe: Optional[bool] = None
    passed: Optional[bool] = None


def series_result_to_out(result: RepeatabilitySeriesResult, sequence_nos: Sequence[int]) -> RepeatabilitySeriesOut:
    """`sequence_nos` must be the same length and order as `result.readings`
    (the caller sorts stored readings by sequence_no before calling
    engine.repeatability.compute_repeatability_series, then passes that same
    sorted sequence_no list here) — the engine result itself carries no
    sequence_no (it only ever sees a plain list of (I, delta_l) pairs), so
    this is the one place the two are zipped back together.
    """
    if len(sequence_nos) != len(result.readings):
        raise ValueError(
            f"sequence_nos length ({len(sequence_nos)}) must match result.readings length ({len(result.readings)})"
        )
    return RepeatabilitySeriesOut(
        series_no=result.series_no,
        L=result.L,
        mpe=result.mpe,
        readings=[
            RepeatabilityReadingRecordOut(
                sequence_no=sequence_no, I=reading.I, delta_l=reading.delta_l, E=reading.E, within_mpe=reading.within_mpe
            )
            for sequence_no, reading in zip(sequence_nos, result.readings)
        ],
        e_max=result.e_max,
        e_min=result.e_min,
        spread=result.spread,
        all_within_mpe=result.all_within_mpe,
        spread_within_mpe=result.spread_within_mpe,
        passed=result.passed,
    )
