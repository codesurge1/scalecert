"""Pydantic v2 contracts for Voltage variations (R76-1 A.5.4, R76-2 page 23)
— clause 11 of the OIML checklist. Unlike the record-only clause-12.x
disturbance tests (app/contracts/disturbance.py), this one DOES compute a
verdict: it reuses the Weighing change-point formula
(engine/weighing.compute_weighing_result) verbatim at a single fixed load,
10e, tested with the instrument powered at three voltage levels — reference,
lower limit, upper limit. No new engine module — this is the Weighing
formula applied to a different scenario, not a different calculation
(mirrors app/contracts/zero_tare.py's same reasoning).
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal

VoltageLevel = Literal["reference", "lower", "upper"]

# Fixed order — also what POST's `level_key` indexes into for the
# `test_readings.sequence_no` column (not null, so every disturbance/
# voltage-variations test reuses its own fixed condition list's position,
# same convention as Tilting repurposing sequence_no for its phase).
VOLTAGE_LEVELS: list[VoltageLevel] = ["reference", "lower", "upper"]
VOLTAGE_LEVEL_LABELS: dict[str, str] = {
    "reference": "Reference value",
    "lower": "Lower limit",
    "upper": "Upper limit",
}


class VoltageVariationsLevelOut(BaseModel):
    """One entry of `GET .../voltage-variations/levels` — the fixed load
    (10e, server-derived, never technician-entered — CLAUDE.md) paired with
    its mpe, so the client knows both before submitting."""

    model_config = ConfigDict(extra="forbid")

    level_key: VoltageLevel
    label: str
    L: StrictDecimal
    mpe: StrictDecimal


class VoltageVariationsReadingSubmitIn(BaseModel):
    """What the client POSTs for one voltage level. `U` is the technician's
    own record of the power-supply voltage actually applied for this level
    (informational — not fed into the Weighing formula, which only uses
    L/I/delta_l/E0); `L` is never submitted, same discipline as every other
    computed test here.
    """

    model_config = ConfigDict(extra="forbid")

    level_key: VoltageLevel
    U: Optional[StrictDecimal] = Field(default=None, description="Power-supply voltage applied for this level, V.")
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal


class VoltageVariationsResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level_key: VoltageLevel
    U: Optional[StrictDecimal] = None
    L: StrictDecimal
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    E: StrictDecimal
    Ec: StrictDecimal
    mpe: StrictDecimal
    passed: bool


class VoltageVariationsReadingRecordOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level_key: VoltageLevel
    U: Optional[StrictDecimal] = None
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    E: StrictDecimal
    Ec: StrictDecimal
    mpe: StrictDecimal
    passed: bool


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> VoltageVariationsReadingRecordOut:
    data = reading_row["data"]
    result = result_row["result"]
    return VoltageVariationsReadingRecordOut(
        level_key=data["level_key"],
        U=data.get("U"),
        I=data["I"],
        delta_l=data["delta_l"],
        E0=data["E0"],
        E=result["E"],
        Ec=result["Ec"],
        mpe=result["mpe"],
        passed=result_row["passed"],
    )
