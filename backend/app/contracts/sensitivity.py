"""Pydantic v2 contracts for the Sensitivity test (R76-1 A.4.9,
engine/sensitivity.py) — non-self-indicating instruments only, tiered pass
threshold (by accuracy class AND Max, not a single number)."""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal


class SensitivityReadingSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence_no: int = Field(ge=0, description="Index into the 3 generated check loads (0..2).")
    permanent_displacement_mm: StrictDecimal


class SensitivityCheckOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    L: StrictDecimal
    mpe: StrictDecimal
    extra_load: StrictDecimal
    threshold_mm: StrictDecimal


class SensitivityResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    L: StrictDecimal
    mpe: StrictDecimal
    extra_load: StrictDecimal
    permanent_displacement_mm: StrictDecimal
    threshold_mm: StrictDecimal
    passed: bool


class SensitivityReadingRecordOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    permanent_displacement_mm: StrictDecimal
    threshold_mm: StrictDecimal
    passed: bool


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> SensitivityReadingRecordOut:
    data = reading_row["data"]
    result = result_row["result"]
    return SensitivityReadingRecordOut(
        sequence_no=reading_row["sequence_no"],
        permanent_displacement_mm=data["permanent_displacement_mm"],
        threshold_mm=result["threshold_mm"],
        passed=result_row["passed"],
    )
