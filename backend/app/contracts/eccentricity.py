"""Pydantic v2 contracts for the Eccentricity test (R76-1 A.4.7, "3.1
weights", engine/eccentricity.py) — same per-reading shape as Weighing
(E, Ec, E0, mpe), but keyed by `position_no` (1-4, R76-2 page 12's sketch:
1=top-left, 2=top-right, 3=bottom-right, 4=bottom-left) instead of
`direction`, and `E0` is submitted fresh with every position (re-measured
before each one, per the form) rather than one session-level value.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal
from engine.types import AccuracyClass, EccentricityPositionResult, VerificationType


class EccentricityReadingIn(BaseModel):
    """One position's reading, engine-ready. `L` is server-supplied from
    engine.eccentricity.generate_eccentricity_load (one fixed load shared
    across all 4 positions) — never technician-entered, same discipline as
    Weighing/Zero-tare. `E0` IS technician-supplied here, per-position
    (unlike Weighing's one session-level E0) — see module docstring."""

    model_config = ConfigDict(extra="forbid")

    position_no: int = Field(ge=1, le=4)
    accuracy_class: AccuracyClass
    verification_type: VerificationType

    e: StrictDecimal
    L: StrictDecimal = Field(description="Server-supplied from generate_eccentricity_load — never technician-entered.")
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal


class EccentricityResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position_no: int
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


class EccentricityReadingSubmitIn(BaseModel):
    """What the client POSTs for one position — no `L`/`accuracy_class`/
    `verification_type`/`e` (server-derived), but `E0` IS here, since it's
    genuinely per-position technician input for this test."""

    model_config = ConfigDict(extra="forbid")

    position_no: int = Field(ge=1, le=4)
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal


class EccentricitySetupOut(BaseModel):
    """`GET .../eccentricity/setup` — the one fixed test load shared across
    all 4 positions, and its mpe (both server-derived, constant regardless
    of how many positions have been submitted so far)."""

    model_config = ConfigDict(extra="forbid")

    L: StrictDecimal
    mpe: StrictDecimal


class EccentricityReadingRecordOut(BaseModel):
    """One row of `GET .../eccentricity/readings` — a previously submitted
    position reading paired with its computed result, read back (never
    recomputed)."""

    model_config = ConfigDict(extra="forbid")

    position_no: int
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    E: StrictDecimal
    Ec: StrictDecimal
    mpe: StrictDecimal
    passed: bool


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> EccentricityReadingRecordOut:
    data = reading_row["data"]
    result = result_row["result"]
    return EccentricityReadingRecordOut(
        position_no=reading_row["position_no"],
        I=data["I"],
        delta_l=data["delta_l"],
        E0=data["E0"],
        E=result["E"],
        Ec=result["Ec"],
        mpe=result["mpe"],
        passed=result_row["passed"],
    )


def reading_to_engine_kwargs(reading: EccentricityReadingIn) -> dict:
    return dict(
        position_no=reading.position_no,
        accuracy_class=reading.accuracy_class,
        verification_type=reading.verification_type,
        e=reading.e,
        L=reading.L,
        I=reading.I,
        delta_l=reading.delta_l,
        E0=reading.E0,
    )


def result_to_out(position_result: EccentricityPositionResult) -> EccentricityResultOut:
    result = position_result.weighing_result
    return EccentricityResultOut(
        position_no=position_result.position_no,
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
