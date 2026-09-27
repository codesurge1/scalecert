"""Pydantic v2 contracts for Damp heat, steady state (clause 13, B.2, R76-2
pages 37-39). THREE runs of the exact same Weighing procedure under
different conditions — a) Initial test (at reference temperature), b) test
at high temperature + 85% relative humidity, c) Final test (at reference
temperature) — reusing `engine.weighing.compute_weighing_result` directly,
same "a Weighing-formula application, not a new engine" precedent
`app/contracts/voltage_variations.py`/`app/contracts/zero_tare.py` already
set. Runs/conditions (`app/contracts/runs.py`, feat/test-runs-conditions)
carry which of a/b/c a reading belongs to — every reading here has a real
`run_id`, never the implicit default/only run Weighing itself allows.

Mirrors `weighing.py`'s shape (`*ReadingIn`/`*ReadingSubmitIn`/`*ResultOut`/
`*ReadingRecordOut` plus the engine-seam adapter functions) rather than
reusing `WeighingReadingSubmitIn` etc. directly — this app's own
established one-contract-module-per-test convention (docs/architecture.md,
Contracts), the same choice `zero_tare.py` already made for an identical
reason.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import Direction, StrictDecimal
from engine.types import AccuracyClass, VerificationType, WeighingResult


class DampHeatReadingIn(BaseModel):
    """One Damp heat reading, engine-ready — field provenance mirrors
    WeighingReadingIn exactly (app/contracts/weighing.py)."""

    model_config = ConfigDict(extra="forbid")

    accuracy_class: AccuracyClass
    verification_type: VerificationType
    direction: Direction

    e: StrictDecimal
    L: StrictDecimal = Field(
        description="Server-supplied from the regenerated Weighing load sequence — never technician-entered."
    )
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal


class DampHeatResultOut(BaseModel):
    """The full derivation returned to the client — mirrors
    engine.types.WeighingResult plus MPE band context, same shape as
    WeighingResultOut."""

    model_config = ConfigDict(extra="forbid")

    L: StrictDecimal
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    E: StrictDecimal
    Ec: StrictDecimal
    mpe: StrictDecimal
    margin: StrictDecimal
    passed: bool

    mpe_in_e: StrictDecimal
    band_lower_m: StrictDecimal
    band_upper_m: Optional[StrictDecimal]


class DampHeatReadingSubmitIn(BaseModel):
    """What the client POSTs for one reading — narrower than
    DampHeatReadingIn, same pattern as WeighingReadingSubmitIn. `run_id` is
    which of the three runs (Initial/High temp+RH/Final) this reading
    belongs to — set up front by `POST .../damp-heat/setup`, so in
    practice always given, but kept `Optional` for contract-shape
    consistency with Weighing's own field."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int = Field(ge=0, description="Index into the session's generated load sequence.")
    direction: Direction
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    run_id: Optional[str] = Field(default=None, description="Which of the three Damp heat runs this reading belongs to.")


class DampHeatReadingRecordOut(BaseModel):
    """One row of `GET .../damp-heat/readings` — a previously submitted
    reading paired with its computed result, read back (never recomputed),
    same pattern as WeighingReadingRecordOut."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    direction: Direction
    run_id: Optional[str] = None
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    E: StrictDecimal
    Ec: StrictDecimal
    mpe: StrictDecimal
    passed: bool


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> DampHeatReadingRecordOut:
    data = reading_row["data"]
    result = result_row["result"]
    return DampHeatReadingRecordOut(
        sequence_no=reading_row["sequence_no"],
        direction=reading_row["direction"],
        run_id=reading_row.get("run_id"),
        I=data["I"],
        delta_l=data["delta_l"],
        E0=data["E0"],
        E=result["E"],
        Ec=result["Ec"],
        mpe=result["mpe"],
        passed=result_row["passed"],
    )


def reading_to_engine_kwargs(reading: DampHeatReadingIn) -> dict:
    return dict(
        accuracy_class=reading.accuracy_class,
        verification_type=reading.verification_type,
        e=reading.e,
        L=reading.L,
        I=reading.I,
        delta_l=reading.delta_l,
        E0=reading.E0,
    )


def result_to_out(result: WeighingResult) -> DampHeatResultOut:
    return DampHeatResultOut(
        L=result.L,
        I=result.I,
        delta_l=result.delta_l,
        E0=result.E0,
        E=result.E,
        Ec=result.Ec,
        mpe=result.mpe,
        margin=result.margin,
        passed=result.passed,
        mpe_in_e=result.mpe_lookup.mpe_in_e,
        band_lower_m=result.mpe_lookup.band_lower_m,
        band_upper_m=result.mpe_lookup.band_upper_m,
    )
