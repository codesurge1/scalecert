"""Pydantic v2 contracts for the Weighing test — the one vertical slice built
so far (docs/plan.md Phase 2). See app/contracts/__init__.py for where the
other six test_type contracts will go later.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import Direction, StrictDecimal
from engine.types import AccuracyClass, LoadKind, VerificationType, WeighingResult


class WeighingReadingIn(BaseModel):
    """One Weighing-test reading, as submitted by the technician's client.

    Field provenance (this contract only validates shape; where each value
    actually comes from is a Phase 2 wiring concern, not this module's job):
      - `I`, `delta_l`: typed directly by the technician — the ONLY two
        numbers they ever enter (CLAUDE.md).
      - `L`: NOT technician-entered. Supplied by the server from the
        generated load sequence (engine.load_sequence.generate_load_sequence)
        and validated here like any other field — never a value the client
        is trusted to invent.
      - `direction`: which pass (up/down) of the bidirectional load sequence
        this reading belongs to.
      - `accuracy_class`, `e`: from the instrument record.
      - `verification_type`: from the test session.
      - `E0`: the zero-point error established earlier in this session.
    """

    model_config = ConfigDict(extra="forbid")

    accuracy_class: AccuracyClass
    verification_type: VerificationType
    direction: Direction

    e: StrictDecimal
    L: StrictDecimal = Field(
        description="Server-supplied from the generated load sequence — never technician-entered."
    )
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal


class WeighingResultOut(BaseModel):
    """The full Weighing-test derivation returned to the client — mirrors
    engine.types.WeighingResult plus the MPE band context, never just a
    pass/fail boolean (CLAUDE.md).
    """

    model_config = ConfigDict(extra="forbid")

    accuracy_class: AccuracyClass
    verification_type: VerificationType

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


class WeighingReadingSubmitIn(BaseModel):
    """What the technician's client actually POSTs for one reading —
    deliberately narrower than `WeighingReadingIn`. `L`, `accuracy_class`,
    `verification_type`, and `e` are NOT here: they come from the server's
    own instrument/session lookup and the regenerated load sequence
    (`sequence_no` is the only thing that ties this submission to an `L`),
    never from the client. The route handler merges this with that
    server-derived context to build the full `WeighingReadingIn` the engine
    seam expects.
    """

    model_config = ConfigDict(extra="forbid")

    sequence_no: int = Field(ge=0, description="Index into the session's generated load sequence.")
    direction: Direction
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    run_id: Optional[str] = Field(
        default=None,
        description=(
            "Which run (feat/test-runs-conditions) this reading belongs to. Omitted/null "
            "means the default/only run — the same behavior as before runs existed."
        ),
    )


class WeighingSequenceEntryOut(BaseModel):
    """One entry of `GET /api/sessions/{id}/weighing/sequence` — mirrors
    engine.types.LoadEntry, plus the `sequence_no` (its stable index) that
    `POST .../readings` expects back."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    L: StrictDecimal
    m: StrictDecimal
    kind: LoadKind
    mpe: StrictDecimal


class WeighingReadingRecordOut(BaseModel):
    """One row of `GET /sessions/{id}/weighing/readings` — a previously
    submitted reading paired with its computed result, so the client can
    reconstruct the R76-2 form table (which cells are filled, their E/Ec,
    pass/fail) on page load/refresh without resubmitting or recomputing
    anything. Built from the stored `test_readings.data` (the
    WeighingReadingIn JSON this reading was submitted as) and its paired
    `test_results.result` (the WeighingResultOut JSON the engine computed) —
    read back, never recomputed.
    """

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


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> WeighingReadingRecordOut:
    """Build a WeighingReadingRecordOut from a raw `test_readings` row and its
    paired `test_results` row (matched by `test_results.reading_id`). Both
    rows' JSONB payloads (`data`, `result`) are already the JSON dumps of
    WeighingReadingIn/WeighingResultOut from submit time — string-valued
    Decimals already — so this only selects fields, nothing is re-parsed or
    recomputed.
    """
    data = reading_row["data"]
    result = result_row["result"]
    return WeighingReadingRecordOut(
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


def reading_to_engine_kwargs(reading: WeighingReadingIn) -> dict:
    """The engine-call seam, inbound: WeighingReadingIn -> the keyword
    arguments engine.weighing.compute_weighing_result expects. Every value on
    `reading` is already a Decimal/enum (the contract parsed it on
    construction) — this just selects the matching keywords; nothing is
    re-parsed, converted, or guessed here.
    """
    return dict(
        accuracy_class=reading.accuracy_class,
        verification_type=reading.verification_type,
        e=reading.e,
        L=reading.L,
        I=reading.I,
        delta_l=reading.delta_l,
        E0=reading.E0,
    )


def result_to_out(result: WeighingResult) -> WeighingResultOut:
    """The engine-call seam, outbound: engine.types.WeighingResult ->
    WeighingResultOut."""
    return WeighingResultOut(
        accuracy_class=result.accuracy_class,
        verification_type=result.verification_type,
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
