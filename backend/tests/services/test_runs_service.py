"""Pure unit tests for app.services.runs — no DB, no HTTP."""

from decimal import Decimal

from app.contracts.common import Direction
from app.contracts.weighing import WeighingReadingRecordOut
from app.services.runs import compare_records, next_ordinal

D = Decimal


def test_next_ordinal_is_zero_for_no_existing_runs():
    assert next_ordinal([]) == 0


def test_next_ordinal_is_one_past_however_many_runs_exist():
    assert next_ordinal([{"id": "r1"}]) == 1
    assert next_ordinal([{"id": "r1"}, {"id": "r2"}]) == 2


def _record(sequence_no, direction, ec, mpe, run_id=None):
    return WeighingReadingRecordOut(
        sequence_no=sequence_no,
        direction=direction,
        run_id=run_id,
        I=D("0"),
        delta_l=D("0"),
        E0=D("0"),
        E=D("0"),
        Ec=D(ec),
        mpe=D(mpe),
        passed=True,
    )


def test_compare_records_matches_by_sequence_no_and_direction():
    records_a = [_record(0, Direction.UP, "0.9", "0.5"), _record(0, Direction.DOWN, "0.2", "0.5")]
    records_b = [_record(0, Direction.UP, "0.3", "0.5"), _record(0, Direction.DOWN, "0.25", "0.5")]

    entries = compare_records(records_a, records_b, run_id_a="run-a", run_id_b="run-b")

    assert len(entries) == 2
    up_entry = next(e for e in entries if e.direction == Direction.UP)
    assert up_entry.variation_error == D("0.6")
    assert up_entry.passed is False
    assert up_entry.run_id_a == "run-a"
    assert up_entry.run_id_b == "run-b"

    down_entry = next(e for e in entries if e.direction == Direction.DOWN)
    assert down_entry.variation_error == D("0.05")
    assert down_entry.passed is True


def test_compare_records_skips_loads_present_in_only_one_run():
    records_a = [_record(0, Direction.UP, "0.3", "0.5"), _record(1, Direction.UP, "0.1", "0.5")]
    records_b = [_record(0, Direction.UP, "0.35", "0.5")]

    entries = compare_records(records_a, records_b, run_id_a=None, run_id_b="run-b")

    assert len(entries) == 1
    assert entries[0].sequence_no == 0


def test_compare_records_returns_empty_list_when_nothing_matches():
    entries = compare_records(
        [_record(0, Direction.UP, "0.1", "0.5")],
        [_record(1, Direction.UP, "0.1", "0.5")],
        run_id_a=None,
        run_id_b=None,
    )
    assert entries == []


def test_compare_records_sorts_by_sequence_no_then_direction():
    records_a = [_record(1, Direction.UP, "0", "0.5"), _record(0, Direction.DOWN, "0", "0.5"), _record(0, Direction.UP, "0", "0.5")]
    records_b = [_record(1, Direction.UP, "0", "0.5"), _record(0, Direction.DOWN, "0", "0.5"), _record(0, Direction.UP, "0", "0.5")]

    entries = compare_records(records_a, records_b, run_id_a=None, run_id_b=None)

    assert [(e.sequence_no, e.direction) for e in entries] == [
        (0, Direction.DOWN),
        (0, Direction.UP),
        (1, Direction.UP),
    ]
