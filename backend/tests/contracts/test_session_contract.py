import pytest
from pydantic import ValidationError

from app.contracts.common import SessionStatus, TestType
from app.contracts.session import SessionIn, session_insert_payload, session_out_from_rows


def test_valid_session_in_parses():
    session = SessionIn(instrument_id="instr-1", verification_type="initial")
    assert session.instrument_id == "instr-1"


def test_session_in_rejects_bad_verification_type():
    with pytest.raises(ValidationError):
        SessionIn(instrument_id="instr-1", verification_type="annual")


def test_session_in_rejects_missing_instrument_id():
    with pytest.raises(ValidationError):
        SessionIn(verification_type="initial")


def test_session_insert_payload_carries_created_by_and_no_status():
    session = SessionIn(instrument_id="instr-1", verification_type="initial")
    payload = session_insert_payload("user-123", session)
    assert payload["created_by"] == "user-123"
    assert "status" not in payload  # the column's own default is the source of truth


def test_session_out_from_rows_includes_test_selections():
    session_row = dict(
        id="sess-1",
        instrument_id="instr-1",
        verification_type="initial",
        status="draft",
        created_by="user-123",
        created_at="2026-01-01T00:00:00Z",
    )
    selection_rows = [
        dict(
            id="sel-1",
            session_id="sess-1",
            test_type="weighing",
            applicable=True,
            na_reason=None,
            zero_device_status=None,
            status="pending",
        )
    ]
    out = session_out_from_rows(session_row, selection_rows)
    assert out.status is SessionStatus.DRAFT
    assert len(out.test_selections) == 1
    assert out.test_selections[0].test_type is TestType.WEIGHING
