"""Pydantic v2 contracts for the Zero/tare device accuracy test — the
Weighing change-point formula (engine/zero_tare.py) applied to a small,
server-derived set of check loads rather than a full load sequence.

Stored under `test_type='weighing'` (db/schema.sql's `test_type` enum
comment names this explicitly: "weighing — ... (incl. zero/tare device
accuracy variant)" — there is no separate 'zero_tare' test_type) but
distinguished from a regular Weighing load-sequence reading by `direction`:
a Weighing-sequence reading always has one (up/down, WeighingReadingSubmitIn
requires it); a zero/tare reading never does — `direction` is left null at
the DB row for every zero/tare insert (see app/repositories/readings.py).
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal
from engine.types import AccuracyClass, VerificationType, WeighingResult


class ZeroTareReadingIn(BaseModel):
    """One zero/tare check reading, engine-ready. Field provenance mirrors
    WeighingReadingIn (app/contracts/weighing.py): `I`/`delta_l` are
    technician-typed; `L` is server-supplied from
    engine.zero_tare.generate_zero_tare_checks, never technician-entered.
    """

    model_config = ConfigDict(extra="forbid")

    accuracy_class: AccuracyClass
    verification_type: VerificationType

    e: StrictDecimal
    L: StrictDecimal = Field(
        description="Server-supplied from generate_zero_tare_checks — never technician-entered."
    )
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal


class ZeroTareResultOut(BaseModel):
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


class ZeroTareReadingSubmitIn(BaseModel):
    """What the client actually POSTs for one zero/tare check — deliberately
    narrower than ZeroTareReadingIn, same pattern as
    WeighingReadingSubmitIn: no `L`/`accuracy_class`/`verification_type`/`e`,
    those come from the server's own instrument/session lookup and the
    regenerated check list."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int = Field(ge=0, description="Index into the zero/tare check list (0..2).")
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal


class ZeroTareCheckOut(BaseModel):
    """One entry of `GET .../zero-tare/checks` — mirrors
    engine.zero_tare.generate_zero_tare_checks' output plus the mpe for that
    check load and the `sequence_no` POST .../readings expects back."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    L: StrictDecimal
    m: StrictDecimal
    mpe: StrictDecimal


class ZeroTareReadingRecordOut(BaseModel):
    """One row of `GET .../zero-tare/readings` — a previously submitted
    check reading paired with its computed result, read back (never
    recomputed), same pattern as WeighingReadingRecordOut."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    E: StrictDecimal
    Ec: StrictDecimal
    mpe: StrictDecimal
    passed: bool


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> ZeroTareReadingRecordOut:
    data = reading_row["data"]
    result = result_row["result"]
    return ZeroTareReadingRecordOut(
        sequence_no=reading_row["sequence_no"],
        I=data["I"],
        delta_l=data["delta_l"],
        E0=data["E0"],
        E=result["E"],
        Ec=result["Ec"],
        mpe=result["mpe"],
        passed=result_row["passed"],
    )


def reading_to_engine_kwargs(reading: ZeroTareReadingIn) -> dict:
    return dict(
        accuracy_class=reading.accuracy_class,
        verification_type=reading.verification_type,
        e=reading.e,
        L=reading.L,
        I=reading.I,
        delta_l=reading.delta_l,
        E0=reading.E0,
    )


def result_to_out(result: WeighingResult) -> ZeroTareResultOut:
    return ZeroTareResultOut(
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
