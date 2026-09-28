"""Pure unit tests for app.services.runs — no DB, no HTTP."""

from decimal import Decimal

from app.contracts.common import Direction
from app.contracts.weighing import WeighingReadingRecordOut
from app.services.runs import compare_records, durability_check_from_entries, ensure_fixed_run_labels, next_ordinal

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


# -- ensure_fixed_run_labels (Damp heat/Endurance's fixed-run setup) -------


def test_ensure_fixed_run_labels_returns_all_labels_when_no_runs_exist():
    missing = ensure_fixed_run_labels([], ["a) Initial test", "c) Final test"])
    assert missing == ["a) Initial test", "c) Final test"]


def test_ensure_fixed_run_labels_returns_only_the_missing_ones():
    existing = [{"run_label": "a) Initial test", "ordinal": 0}]
    missing = ensure_fixed_run_labels(existing, ["a) Initial test", "c) Final test"])
    assert missing == ["c) Final test"]


def test_ensure_fixed_run_labels_is_idempotent_once_all_exist():
    existing = [{"run_label": "a) Initial test"}, {"run_label": "c) Final test"}]
    missing = ensure_fixed_run_labels(existing, ["a) Initial test", "c) Final test"])
    assert missing == []


# -- durability_check_from_entries (Endurance's own aggregate) -------------


def _comparison_entry(ec_a, ec_b, mpe):
    from app.contracts.runs import RunComparisonEntryOut

    variation_error = abs(D(ec_a) - D(ec_b))
    return RunComparisonEntryOut(
        sequence_no=0,
        direction=Direction.UP,
        run_id_a="run-initial",
        run_id_b="run-final",
        Ec_a=D(ec_a),
        Ec_b=D(ec_b),
        variation_error=variation_error,
        mpe=D(mpe),
        margin=D(mpe) - variation_error,
        passed=variation_error <= D(mpe),
    )


def test_durability_check_from_entries_all_passing():
    entries = [_comparison_entry("0.1", "0.1", "0.5"), _comparison_entry("0.2", "0.3", "0.5")]
    result = durability_check_from_entries(entries)
    assert result.all_passed is True
    assert len(result.comparisons) == 2


def test_durability_check_from_entries_one_failing_load_fails_the_whole_check():
    entries = [_comparison_entry("0.1", "0.1", "0.5"), _comparison_entry("0.9", "0.1", "0.5")]
    result = durability_check_from_entries(entries)
    assert result.all_passed is False


def test_durability_check_from_entries_empty_never_passes():
    result = durability_check_from_entries([])
    assert result.all_passed is False
    assert result.comparisons == ()
