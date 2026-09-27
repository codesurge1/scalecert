"""Pydantic v2 contracts for the Discrimination test (R76-1 A.4.8,
engine/discrimination.py) — THREE distinct sub-procedures selected by the
instrument's own `indication_type`, never a client-submitted flag (same
"derived, not chosen" discipline as accuracy_class): `variant` on the output
models says which one actually ran. One submit-in model covers all three,
with the fields each variant doesn't use left `None` — the service layer
(app/services/discrimination.py) is what enforces which subset is actually
required for the instrument's determined variant.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal

DiscriminationVariant = Literal["analog", "non_self_indicating", "digital"]


class DiscriminationReadingSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence_no: int = Field(ge=0, description="Index into the 3 generated check loads (0..2).")
    I1: Optional[StrictDecimal] = None
    I2: Optional[StrictDecimal] = None
    visible_displacement: Optional[bool] = None


class DiscriminationCheckOut(BaseModel):
    """One entry of `GET .../discrimination/checks` — the generated check
    load, its mpe (None for the digital variant, which has no mpe lookup at
    all), and which sub-procedure applies to this instrument."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    L: StrictDecimal
    mpe: Optional[StrictDecimal] = None
    variant: DiscriminationVariant


class DiscriminationResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: DiscriminationVariant
    L: StrictDecimal
    mpe: Optional[StrictDecimal] = None
    d: Optional[StrictDecimal] = None
    I1: Optional[StrictDecimal] = None
    I2: Optional[StrictDecimal] = None
    difference: Optional[StrictDecimal] = None
    threshold: Optional[StrictDecimal] = None
    extra_load: Optional[StrictDecimal] = None
    visible_displacement: Optional[bool] = None
    passed: bool


class DiscriminationReadingRecordOut(BaseModel):
    """One row of `GET .../discrimination/readings` — a previously submitted
    check reading paired with its computed result, read back (never
    recomputed)."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    variant: DiscriminationVariant
    I1: Optional[StrictDecimal] = None
    I2: Optional[StrictDecimal] = None
    visible_displacement: Optional[bool] = None
    difference: Optional[StrictDecimal] = None
    passed: bool


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> DiscriminationReadingRecordOut:
    data = reading_row["data"]
    result = result_row["result"]
    return DiscriminationReadingRecordOut(
        sequence_no=reading_row["sequence_no"],
        variant=result["variant"],
        I1=data.get("I1"),
        I2=data.get("I2"),
        visible_displacement=data.get("visible_displacement"),
        difference=result.get("difference"),
        passed=result_row["passed"],
    )
