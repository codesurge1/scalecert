"""Pydantic v2 contracts for runs/conditions (feat/test-runs-conditions) —
the concept behind every OIML test that re-runs the SAME procedure under
different conditions (clause 1 Weighing at multiple temperatures, clause 13
Damp heat, clause 15 Endurance). `TestRunCreateIn`/`TestRunOut` are already
generic across `test_type` (mirrors `db/schema.sql`'s `test_runs` table,
which is one table across every test, same "hybrid design" as
`test_readings`/`test_results`); only Weighing has a router wired to them so
far (docs/architecture.md).

`RunComparisonEntryOut` mirrors `engine.types.RunComparisonResult`, plus the
`sequence_no`/`direction` that identify WHICH load the comparison is for and
the two run ids being compared — never just a bare pass/fail boolean,
same "full derivation, not just a verdict" discipline as every other
contract in this app.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import Direction, StrictDecimal, TestType
from engine.types import RunComparisonResult


class TestRunCreateIn(BaseModel):
    """What the client POSTs to create a new run. `test_type`, `ordinal`,
    `created_by` are never client-supplied — the route path fixes the
    test_type, and the server derives the ordinal (next available slot)
    and created_by (the caller's own id)."""

    model_config = ConfigDict(extra="forbid")

    run_label: str = Field(min_length=1, max_length=200)
    conditions: Optional[dict] = None


class TestRunOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    test_type: TestType
    run_label: str
    conditions: Optional[dict]
    ordinal: int
    created_by: str
    created_at: str


def run_row_to_out(row: dict) -> TestRunOut:
    return TestRunOut(
        id=row["id"],
        session_id=row["session_id"],
        test_type=row["test_type"],
        run_label=row["run_label"],
        conditions=row.get("conditions"),
        ordinal=row["ordinal"],
        created_by=row["created_by"],
        created_at=row["created_at"],
    )


class RunComparisonEntryOut(BaseModel):
    """One load's cross-run comparison — mirrors engine.types.RunComparisonResult
    plus the load identity (sequence_no/direction) and which two runs were
    compared (either id may be None, meaning the default/only run)."""

    model_config = ConfigDict(extra="forbid")

    sequence_no: int
    direction: Optional[Direction] = None
    run_id_a: Optional[str] = None
    run_id_b: Optional[str] = None

    Ec_a: StrictDecimal
    Ec_b: StrictDecimal
    variation_error: StrictDecimal
    mpe: StrictDecimal
    margin: StrictDecimal
    passed: bool


def comparison_result_to_out(
    result: RunComparisonResult,
    *,
    sequence_no: int,
    direction: Optional[Direction],
    run_id_a: Optional[str],
    run_id_b: Optional[str],
) -> RunComparisonEntryOut:
    return RunComparisonEntryOut(
        sequence_no=sequence_no,
        direction=direction,
        run_id_a=run_id_a,
        run_id_b=run_id_b,
        Ec_a=result.Ec_a,
        Ec_b=result.Ec_b,
        variation_error=result.variation_error,
        mpe=result.mpe,
        margin=result.margin,
        passed=result.passed,
    )
