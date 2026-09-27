"""Pure unit tests for app.services.certificate — no DB, no reportlab."""

from app.services.certificate import (
    TestSummary,
    series_aggregate_summary,
    simple_passed_summary,
    state_summary,
    weighing_overall_passed,
    weighing_rows_from_db,
)


def _reading(row_id, sequence_no, direction, created_at, L="100"):
    return {
        "id": row_id,
        "sequence_no": sequence_no,
        "direction": direction,
        "data": {"L": L, "I": "100.4", "delta_l": "0"},
        "created_at": created_at,
    }


def _result(reading_id, *, E="0.4", Ec="0.4", mpe="0.5", passed=True):
    return {"reading_id": reading_id, "result": {"E": E, "Ec": Ec, "mpe": mpe}, "passed": passed}


# ---------------------------------------------------------------------------
# weighing_rows_from_db / weighing_overall_passed
# ---------------------------------------------------------------------------
def test_weighing_rows_from_db_excludes_zero_tare_rows_with_null_direction():
    reading_rows = [
        _reading("r-up", 0, "up", "2026-01-01T00:00:00Z"),
        _reading("r-down", 0, "down", "2026-01-01T00:00:01Z"),
        _reading("r-zero-tare", 0, None, "2026-01-01T00:00:02Z"),  # direction is null -> zero/tare
    ]
    result_rows = [_result("r-up"), _result("r-down"), _result("r-zero-tare")]

    rows = weighing_rows_from_db(reading_rows, result_rows)
    assert len(rows) == 2
    assert {row.direction for row in rows} == {"up", "down"}


def test_weighing_rows_from_db_dedupes_to_latest_per_sequence_and_direction():
    reading_rows = [
        _reading("r-old", 0, "up", "2026-01-01T00:00:00Z", L="100"),
        _reading("r-new", 0, "up", "2026-01-01T00:00:05Z", L="100"),
    ]
    result_rows = [_result("r-old", E="0.4", passed=True), _result("r-new", E="0.6", passed=False)]

    rows = weighing_rows_from_db(reading_rows, result_rows)
    assert len(rows) == 1
    assert rows[0].E == "0.6"
    assert rows[0].passed is False


def test_weighing_rows_from_db_skips_readings_with_no_matching_result():
    reading_rows = [_reading("r-orphan", 0, "up", "2026-01-01T00:00:00Z")]
    rows = weighing_rows_from_db(reading_rows, [])
    assert rows == []


def test_weighing_rows_from_db_sorted_by_sequence_then_direction():
    reading_rows = [
        _reading("r1", 1, "up", "2026-01-01T00:00:00Z"),
        _reading("r0-down", 0, "down", "2026-01-01T00:00:01Z"),
        _reading("r0-up", 0, "up", "2026-01-01T00:00:02Z"),
    ]
    result_rows = [_result("r1"), _result("r0-down"), _result("r0-up")]
    rows = weighing_rows_from_db(reading_rows, result_rows)
    assert [(r.sequence_no, r.direction) for r in rows] == [(0, "down"), (0, "up"), (1, "up")]


def test_weighing_overall_passed_none_when_no_rows():
    assert weighing_overall_passed([]) is None


def test_weighing_overall_passed_true_when_all_passed():
    reading_rows = [_reading("r-up", 0, "up", "2026-01-01T00:00:00Z"), _reading("r-down", 0, "down", "2026-01-01T00:00:01Z")]
    result_rows = [_result("r-up", passed=True), _result("r-down", passed=True)]
    rows = weighing_rows_from_db(reading_rows, result_rows)
    assert weighing_overall_passed(rows) is True


def test_weighing_overall_passed_false_when_any_failed():
    reading_rows = [_reading("r-up", 0, "up", "2026-01-01T00:00:00Z"), _reading("r-down", 0, "down", "2026-01-01T00:00:01Z")]
    result_rows = [_result("r-up", passed=True), _result("r-down", passed=False)]
    rows = weighing_rows_from_db(reading_rows, result_rows)
    assert weighing_overall_passed(rows) is False


# ---------------------------------------------------------------------------
# simple_passed_summary — zero-tare/eccentricity/discrimination/sensitivity
# ---------------------------------------------------------------------------
def test_simple_passed_summary_not_performed_when_empty():
    summary = simple_passed_summary("Eccentricity", [])
    assert summary == TestSummary(label="Eccentricity", performed=False, passed=None)


def test_simple_passed_summary_pass_when_all_true():
    summary = simple_passed_summary("Eccentricity", [True, True, True])
    assert summary.performed is True
    assert summary.passed is True


def test_simple_passed_summary_fail_when_any_false():
    summary = simple_passed_summary("Eccentricity", [True, False, True])
    assert summary.passed is False


# ---------------------------------------------------------------------------
# series_aggregate_summary — Repeatability's real per-series verdict
# (mpe AND spread), not a naive per-reading scan.
# ---------------------------------------------------------------------------
class _FakeSeries:
    def __init__(self, readings, passed):
        self.readings = readings
        self.passed = passed


def test_series_aggregate_summary_not_performed_when_no_readings_at_all():
    series_list = [_FakeSeries([], None), _FakeSeries([], None)]
    summary = series_aggregate_summary("Repeatability", series_list)
    assert summary.performed is False
    assert summary.passed is None


def test_series_aggregate_summary_incomplete_when_one_series_unresolved():
    series_list = [_FakeSeries([("r", "1", "0")], True), _FakeSeries([], None)]
    summary = series_aggregate_summary("Repeatability", series_list)
    assert summary.performed is True
    assert summary.passed is None


def test_series_aggregate_summary_fail_when_one_series_fails_even_if_the_other_passes():
    # This is the exact case a naive "all per-reading passed" scan would
    # get wrong: a series can fail on the SPREAD criterion even if every
    # individual reading's own |E| <= mpe.
    series_list = [_FakeSeries([("r", "1", "0")], True), _FakeSeries([("r", "1", "0")], False)]
    summary = series_aggregate_summary("Repeatability", series_list)
    assert summary.performed is True
    assert summary.passed is False


def test_series_aggregate_summary_pass_when_both_series_pass():
    series_list = [_FakeSeries([("r", "1", "0")], True), _FakeSeries([("r", "1", "0")], True)]
    summary = series_aggregate_summary("Repeatability", series_list)
    assert summary.passed is True


# ---------------------------------------------------------------------------
# state_summary — Tilting's real whole-dataset verdict.
# ---------------------------------------------------------------------------
class _FakeState:
    def __init__(self, readings, passed):
        self.readings = readings
        self.passed = passed


def test_state_summary_not_performed_when_no_readings():
    summary = state_summary("Tilting", _FakeState([], None))
    assert summary.performed is False
    assert summary.passed is None


def test_state_summary_uses_the_states_own_passed_value():
    summary = state_summary("Tilting", _FakeState([object()], False))
    assert summary.performed is True
    assert summary.passed is False
