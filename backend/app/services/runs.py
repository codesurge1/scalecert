"""Pure orchestration for runs/conditions (feat/test-runs-conditions) and
cross-run comparison — no DB, no HTTP. `compare_records` is deliberately
generic over any reading-record shape that carries `sequence_no`,
`direction`, `Ec`, and `mpe` (today only `WeighingReadingRecordOut` does) so
Damp heat and Endurance can reuse it unmodified once they're built.
"""

from typing import Optional, Protocol

from app.contracts.common import Direction
from app.contracts.runs import RunComparisonEntryOut, comparison_result_to_out
from engine.comparison import compute_run_comparison


def next_ordinal(existing_runs: list[dict]) -> int:
    """The next run's display/creation order — one past however many runs
    already exist for this session+test_type. 0-based: the first run a
    technician explicitly creates gets ordinal 0 (the implicit default run,
    NULL run_id, has no ordinal of its own — it isn't a `test_runs` row)."""
    return len(existing_runs)


class _ComparableRecord(Protocol):
    sequence_no: int
    direction: Direction
    Ec: object
    mpe: object


def compare_records(
    records_a: list[_ComparableRecord],
    records_b: list[_ComparableRecord],
    *,
    run_id_a: Optional[str],
    run_id_b: Optional[str],
) -> list[RunComparisonEntryOut]:
    """Match two runs' reading records by (sequence_no, direction) — the
    same load, tested in each run — and compute the variation error at
    every load both runs actually have a reading for. Loads present in only
    one run are silently skipped (nothing to compare yet), never an error.
    """
    by_key_b = {(record.sequence_no, record.direction): record for record in records_b}
    entries = []
    for record_a in records_a:
        record_b = by_key_b.get((record_a.sequence_no, record_a.direction))
        if record_b is None:
            continue
        comparison = compute_run_comparison(Ec_a=record_a.Ec, Ec_b=record_b.Ec, mpe=record_a.mpe)
        entries.append(
            comparison_result_to_out(
                comparison,
                sequence_no=record_a.sequence_no,
                direction=record_a.direction,
                run_id_a=run_id_a,
                run_id_b=run_id_b,
            )
        )
    entries.sort(key=lambda entry: (entry.sequence_no, entry.direction.value if entry.direction else ""))
    return entries
