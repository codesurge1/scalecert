"""Pure unit tests for app.services.repeatability — no DB, no HTTP."""

from decimal import Decimal

from app.contracts.common import IndicationType
from app.contracts.instrument import InstrumentParams
from app.contracts.repeatability import RepeatabilityReadingSubmitIn
from app.services.repeatability import build_series_load, compute_result_for_submission, compute_series, series_mpe
from engine.types import AccuracyClass, VerificationType

D = Decimal

# Max=1000g, e=1g, Class III -> series 1 (L=500, m=500) is exactly on the
# Band-1/Band-2 edge -> mpe=0.5g; series 2 (L=1000, m=1000) is in Band 2 ->
# mpe=1.0g — same fixture reasoning as tests/test_repeatability.py, so the
# two series provably differ.
_INSTRUMENT = InstrumentParams(
    accuracy_class=AccuracyClass.III,
    e_value=D("1"),
    max_capacity=D("1000"),
    min_capacity=D("10"),
    indication_type=IndicationType.DIGITAL,
    is_mobile=False,
    d_value=None,
)


def test_build_series_load_matches_engine_convention():
    assert build_series_load(_INSTRUMENT, 1) == D("500")
    assert build_series_load(_INSTRUMENT, 2) == D("1000")


def test_series_mpe_works_with_zero_readings():
    assert series_mpe(_INSTRUMENT, VerificationType.INITIAL, 1) == D("0.5")
    assert series_mpe(_INSTRUMENT, VerificationType.INITIAL, 2) == D("1.0")


def test_compute_series_with_no_stored_readings_is_not_started():
    series = compute_series(_INSTRUMENT, VerificationType.INITIAL, 1, [])
    assert series.series_no == 1
    assert series.L == D("500")
    assert series.mpe == D("0.5")
    assert series.readings == []
    assert series.passed is None
    assert series.spread is None


def test_compute_series_recomputes_from_stored_readings_sorted_by_sequence_no():
    # Deliberately out of order and with delta_l = e/2 (cancels the engine's
    # +1/2e term, so E = I - L directly), same trick as the engine tests.
    stored = [(2, D("500.3"), D("0.5")), (0, D("500.1"), D("0.5")), (1, D("500.2"), D("0.5"))]
    series = compute_series(_INSTRUMENT, VerificationType.INITIAL, 1, stored)
    assert [r.sequence_no for r in series.readings] == [0, 1, 2]
    assert [r.E for r in series.readings] == [D("0.1"), D("0.2"), D("0.3")]
    assert series.spread == D("0.2")
    assert series.passed is True


def test_compute_result_for_submission_merges_with_existing_readings():
    existing = [(0, D("500.1"), D("0.5")), (1, D("500.2"), D("0.5"))]
    submission = RepeatabilityReadingSubmitIn(series_no=1, sequence_no=2, I="500.3", delta_l="0.5")

    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL, existing)

    assert result.this_reading_E == D("0.3")
    assert result.this_reading_within_mpe is True
    assert len(result.series_out.readings) == 3
    assert result.series_out.spread == D("0.2")


def test_compute_result_for_submission_resubmission_overwrites_not_duplicates():
    # A second submission for the same sequence_no must replace, not add —
    # matching the "resubmission is a second insert, dedup to latest"
    # convention the caller (the router) is responsible for applying to
    # what it fetches from the DB before calling this function.
    existing = [(0, D("500.1"), D("0.5"))]
    submission = RepeatabilityReadingSubmitIn(series_no=1, sequence_no=0, I="500.9", delta_l="0.5")

    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL, existing)

    assert len(result.series_out.readings) == 1
    assert result.series_out.readings[0].E == D("0.9")


def test_compute_result_for_submission_individual_failure_does_not_prevent_series_out():
    # mpe=0.5g; this reading's own E=0.9 exceeds it -> within_mpe False, but
    # the series-level object is still returned (not an exception) — the
    # caller decides what "failed" means for storage/display.
    submission = RepeatabilityReadingSubmitIn(series_no=1, sequence_no=0, I="500.9", delta_l="0.5")
    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL, [])

    assert result.this_reading_within_mpe is False
    assert result.series_out.all_within_mpe is False
    assert result.series_out.passed is False
