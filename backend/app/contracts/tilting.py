"""Pydantic v2 contracts for the Tilting test (R76-1 A.5.1, A.5.1.1-A.5.1.3,
engine/tilting.py) — the minimal 8.3.3/4.18 slice: reference + 4 tilted
positions, each read unloaded then at two loaded rows. Like Repeatability,
the pass criteria are whole-set properties (not any single reading), so the
primary output shape here is `TiltingStateOut` — the full current state,
recomputed from all stored readings on every GET/POST, not a per-reading
result.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal

TiltingPhase = Literal["unloaded", "loaded_l", "loaded_max"]


class TiltingReadingSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: TiltingPhase
    position_no: int = Field(ge=1, le=5, description="1 = reference position, 2-5 = tilted positions.")
    I: StrictDecimal
    delta_l: StrictDecimal


class TiltingReadingRecordOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: TiltingPhase
    position_no: int
    I: StrictDecimal
    delta_l: StrictDecimal
    E: StrictDecimal
    Ec: Optional[StrictDecimal] = None  # None for the unloaded phase (no E0 to correct against)


class TiltingStateOut(BaseModel):
    """The full current state of the Tilting test: L/mpe for both loaded
    rows (known before any reading is submitted), every reading submitted
    so far, and the two pass criteria — each Optional/None until enough
    readings exist to compute it (position 1, the reference, must be among
    what's submitted for that phase)."""

    model_config = ConfigDict(extra="forbid")

    L: StrictDecimal
    max_capacity: StrictDecimal
    mpe_l: StrictDecimal
    mpe_max: StrictDecimal
    readings: list[TiltingReadingRecordOut] = []

    unloaded_max_abs_deviation: Optional[StrictDecimal] = None
    unloaded_limit: Optional[StrictDecimal] = None
    unloaded_within_limit: Optional[bool] = None

    loaded_l_max_abs_deviation: Optional[StrictDecimal] = None
    loaded_l_within_mpe: Optional[bool] = None

    loaded_max_max_abs_deviation: Optional[StrictDecimal] = None
    loaded_max_within_mpe: Optional[bool] = None

    passed: Optional[bool] = None
