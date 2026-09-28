"""Pure unit tests for app.services.endurance — no DB, no HTTP. Same shape
as test_weighing_service.py/test_damp_heat_service.py.
"""

from decimal import Decimal

import pytest

from app.contracts.common import IndicationType
from app.contracts.endurance import EnduranceReadingSubmitIn
from app.contracts.instrument import InstrumentParams
from app.services.endurance import (
    FINAL_RUN_LABEL,
    FIXED_RUN_LABELS,
    SequenceNumberOutOfRange,
    build_sequence,
    compute_result_for_submission,
    load_entry_for_sequence_no,
)
from engine.types import AccuracyClass, VerificationType

D = Decimal

_INSTRUMENT = InstrumentParams(
    accuracy_class=AccuracyClass.III,
    e_value=D("1"),
    max_capacity=D("5000"),
    min_capacity=D("10"),
    indication_type=IndicationType.DIGITAL,
    is_mobile=False,
    d_value=None,
)


def test_fixed_run_labels_has_exactly_two_labelled_a_c():
    assert len(FIXED_RUN_LABELS) == 2
    assert FIXED_RUN_LABELS[0].startswith("a)")
    assert FIXED_RUN_LABELS[1].startswith("c)")


def test_final_run_label_is_the_second_fixed_label():
    assert FINAL_RUN_LABEL == FIXED_RUN_LABELS[1]


def test_build_sequence_returns_at_least_five_sorted_entries():
    sequence = build_sequence(_INSTRUMENT, VerificationType.INITIAL)
    assert len(sequence) >= 5
    assert [entry.L for entry in sequence] == sorted(entry.L for entry in sequence)


def test_load_entry_for_sequence_no_valid_index():
    sequence = build_sequence(_INSTRUMENT, VerificationType.INITIAL)
    assert load_entry_for_sequence_no(sequence, 0) is sequence[0]


@pytest.mark.parametrize("bad_index", [-1, 9999])
def test_load_entry_for_sequence_no_out_of_range(bad_index):
    sequence = build_sequence(_INSTRUMENT, VerificationType.INITIAL)
    with pytest.raises(SequenceNumberOutOfRange):
        load_entry_for_sequence_no(sequence, bad_index)


def test_compute_result_for_submission_end_to_end_pure():
    sequence = build_sequence(_INSTRUMENT, VerificationType.INITIAL)
    entry0 = sequence[0]

    submission = EnduranceReadingSubmitIn(
        sequence_no=0,
        direction="up",
        I=str(entry0.L + D("0.1")),
        delta_l="0.5",
        E0="0",
        run_id="run-final",
    )
    result = compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)

    assert result.entry == entry0
    assert result.reading.L == entry0.L
    assert result.result_out.E == D("0.1")
    assert result.result_out.Ec == D("0.1")
    assert result.result_out.mpe == entry0.mpe
    assert result.result_out.passed == (D("0.1") <= entry0.mpe)


def test_compute_result_for_submission_raises_for_out_of_range_sequence_no():
    sequence = build_sequence(_INSTRUMENT, VerificationType.INITIAL)
    submission = EnduranceReadingSubmitIn(sequence_no=len(sequence), direction="up", I="1", delta_l="0", E0="0")
    with pytest.raises(SequenceNumberOutOfRange):
        compute_result_for_submission(submission, _INSTRUMENT, VerificationType.INITIAL)
