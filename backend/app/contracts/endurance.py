"""Pydantic v2 contracts for Endurance (clause 15, A.6, R76-2 pages 46-47).
TWO runs of the exact same Weighing procedure — a) Initial test, c) Final
test — around a non-computed "b) Performance of the test" cycling step
(number of loadings, load applied — recorded, never computed; there is
nothing here for an engine to do, same reasoning
`app/contracts/disturbance.py` already established for a different kind of
non-computed step). Reuses `engine.weighing.compute_weighing_result`
directly for a) and c), and `engine.comparison.compute_run_comparison` /
`compute_durability_check` for the form's own extra "Durability error due
to wear and tear = |Ec_initial - Ec_final|" column and its all-loads-must-
pass verdict — no new error-calculation math anywhere in this module.

Mirrors `weighing.py`'s shape for the two Weighing-formula runs (same
established one-contract-module-per-test convention as `damp_heat.py`),
plus two contracts unique to this test: `EnduranceCyclingIn` (the b) step
— stored as `test_runs.conditions` JSONB on the Final run, per
feat/test-runs-conditions' "runs carry condition metadata" design, not a
new column) and `DurabilityCheckOut` (wraps `engine.types.DurabilityCheckResult`).
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal, Direction
from app.contracts.runs import RunComparisonEntryOut
from engine.types import AccuracyClass, DurabilityCheckResult, VerificationType, WeighingResult


class EnduranceReadingIn(BaseModel):
    """One Endurance a)/c) reading, engine-ready — field provenance
    mirrors WeighingReadingIn exactly (app/contracts/weighing.py)."""

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


class EnduranceResultOut(BaseModel):
    """The full derivation returned to the client — mirrors
    engine.types.WeighingResult plus MPE band context, same shape as
    WeighingResultOut. The durability-error column itself is NOT part of
    this per-reading result — it's a cross-run (Initial vs Final)
    property, surfaced separately by GET .../endurance/durability."""

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


class EnduranceReadingSubmitIn(BaseModel):
    """What the client POSTs for one a)/c) reading — `run_id` is which of
    the two runs (Initial/Final) this reading belongs to, set up front by
    `POST .../endurance/setup` (kept `Optional`, same contract-shape
    consistency as Damp heat/Weighing)."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int = Field(ge=0, description="Index into the session's generated load sequence.")
    direction: Direction
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    run_id: Optional[str] = Field(default=None, description="Which of the two Endurance runs this reading belongs to.")


class EnduranceReadingRecordOut(BaseModel):
    """One row of `GET .../endurance/readings` — read back, never
    recomputed, same pattern as WeighingReadingRecordOut."""

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


class EnduranceCyclingIn(BaseModel):
    """b) Performance of the test (R76-2 page 47) — number of loadings and
    the load applied during cycling. Purely recorded, never computed
    (there is no formula here — the instrument is simply cycled N times).
    Stored as `test_runs.conditions` JSONB on the Final run
    (feat/test-runs-conditions' own "conditions carry per-run metadata"
    design) rather than a new column — see ADR-0011."""

    model_config = ConfigDict(extra="forbid")

    number_of_loadings: Optional[int] = Field(default=None, ge=0)
    load_applied: Optional[StrictDecimal] = None


class DurabilityCheckOut(BaseModel):
    """`GET .../endurance/durability`'s response — wraps
    engine.types.DurabilityCheckResult: every load's own comparison
    (RunComparisonEntryOut, already carrying Ec_a/Ec_b/variation_error/mpe/
    passed) plus the aggregate `all_passed` the form's own "Check if the
    durability error due to wear and tear is <= mpe" line requires — never
    just the bare aggregate boolean."""

    model_config = ConfigDict(extra="forbid")

    comparisons: list[RunComparisonEntryOut]
    all_passed: bool


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> EnduranceReadingRecordOut:
    data = reading_row["data"]
    result = result_row["result"]
    return EnduranceReadingRecordOut(
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


def reading_to_engine_kwargs(reading: EnduranceReadingIn) -> dict:
    return dict(
        accuracy_class=reading.accuracy_class,
        verification_type=reading.verification_type,
        e=reading.e,
        L=reading.L,
        I=reading.I,
        delta_l=reading.delta_l,
        E0=reading.E0,
    )


def result_to_out(result: WeighingResult) -> EnduranceResultOut:
    return EnduranceResultOut(
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


def durability_result_to_out(result: DurabilityCheckResult, comparisons: list[RunComparisonEntryOut]) -> DurabilityCheckOut:
    """comparisons is the already-built RunComparisonEntryOut list (with
    sequence_no/direction/run ids) — result carries the SAME underlying
    RunComparisonResult objects plus all_passed, but no load identity, so
    the caller passes both rather than this function re-deriving one from
    the other."""
    return DurabilityCheckOut(comparisons=comparisons, all_passed=result.all_passed)
