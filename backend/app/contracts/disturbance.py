"""Pydantic v2 contracts shared by every 'record-only' electrical
disturbance test (clause 12.x): AC mains voltage dips & short interruptions
(12.1), electrical bursts (12.2), electrostatic discharges (12.4) — and,
when built, surges (12.3), radiated EM fields (12.5), conducted RF fields
(12.6), road-vehicle transients (12.7).

Unlike every other test in this app, these require physical EMC test
equipment the software has no way to drive or measure — a disturbance
generator, an antenna, a battery-transient simulator. There is nothing to
compute: R 76-2's own pass rule for each of these forms is literally "check
if a significant fault occurred" — a fault the TECHNICIAN observes at the
bench (comparing the post-disturbance indication against the pre-disturbance
one and judging whether the difference exceeds e, or whether the
instrument's own fault-detection triggered) and records here. So there is
no engine module for any of these (CLAUDE.md: "Don't build... the 5 new
engines") — the API's only job is to validate that a submitted
`condition_key` is one of that test's own fixed, predefined condition list
(read from the OIML form itself — see app/services/disturbance.py) and
store the technician's observation.

`test_readings.sequence_no` is repurposed as that condition's index into
its own fixed list (0-based) — the same "reuse the existing not-null
integer column for a different discriminator" convention Tilting already
established for its phase.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import StrictDecimal


class DisturbanceConditionOut(BaseModel):
    """One entry of `GET .../{test}/conditions` — the fixed, standardized
    test condition this row of the form represents (e.g. "40 % for 10
    cycles", "L -> ground, positive"). `has_fault_check` is false for a
    form's "Without disturbance" baseline rows, which record only a
    reference Indication — the form itself greys out their No/Yes cells,
    since there is no disturbance applied yet to check a fault against."""

    model_config = ConfigDict(extra="forbid")

    condition_key: str
    label: str
    group: Optional[str] = None
    has_fault_check: bool = True


class DisturbanceReadingSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_key: str
    indication: Optional[StrictDecimal] = None
    significant_fault: bool = False
    remarks: Optional[str] = None


class DisturbanceResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_key: str
    indication: Optional[StrictDecimal] = None
    significant_fault: bool
    remarks: Optional[str] = None
    passed: bool


class DisturbanceReadingRecordOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_key: str
    indication: Optional[StrictDecimal] = None
    significant_fault: bool
    remarks: Optional[str] = None
    passed: bool


def reading_and_result_to_record_out(reading_row: dict, result_row: dict) -> DisturbanceReadingRecordOut:
    data = reading_row["data"]
    return DisturbanceReadingRecordOut(
        condition_key=data["condition_key"],
        indication=data.get("indication"),
        significant_fault=data["significant_fault"],
        remarks=data.get("remarks"),
        passed=result_row["passed"],
    )
