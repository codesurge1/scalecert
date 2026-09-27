import pytest
from pydantic import ValidationError

from app.contracts.common import SessionStatus, TestType
from app.contracts.session import SessionIn, SessionReturnIn, session_insert_payload, session_out_from_rows

_INSTRUMENT_ID = "11111111-1111-4111-8111-111111111111"


def test_valid_session_in_parses():
    session = SessionIn(instrument_id=_INSTRUMENT_ID, verification_type="initial")
    assert str(session.instrument_id) == _INSTRUMENT_ID


def test_session_in_rejects_bad_verification_type():
    with pytest.raises(ValidationError):
        SessionIn(instrument_id=_INSTRUMENT_ID, verification_type="annual")


def test_session_in_rejects_missing_instrument_id():
    with pytest.raises(ValidationError):
        SessionIn(verification_type="initial")


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "", "undefined", "null", "instr-1"])
def test_session_in_rejects_malformed_instrument_id(bad_id):
    # The exact frontend-bug shape (empty/"undefined"/non-UUID) that used to
    # reach Postgres as a raw string and 500 on "invalid input syntax for
    # type uuid" — now a clean 422 at the contract layer, before any DB call.
    with pytest.raises(ValidationError):
        SessionIn(instrument_id=bad_id, verification_type="initial")


def test_session_insert_payload_carries_created_by_and_no_status():
    session = SessionIn(instrument_id=_INSTRUMENT_ID, verification_type="initial")
    payload = session_insert_payload("user-123", session)
    assert payload["created_by"] == "user-123"
    assert payload["instrument_id"] == _INSTRUMENT_ID  # UUID4 serializes back to its string form
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
    # Lifecycle fields all default to None when the row has none of them
    # (this fixture predates the lifecycle columns being populated) —
    # .get() in session_out_from_rows, never a bare KeyError.
    assert out.submitted_at is None
    assert out.approved_by is None
    assert out.certificate_number is None
    assert out.return_reason is None


def test_session_out_from_rows_carries_the_lifecycle_trail():
    session_row = dict(
        id="sess-1",
        instrument_id="instr-1",
        verification_type="initial",
        status="issued",
        created_by="user-123",
        created_at="2026-01-01T00:00:00Z",
        submitted_at="2026-01-02T00:00:00Z",
        approved_by="user-approver",
        approved_at="2026-01-03T00:00:00Z",
        issued_at="2026-01-04T00:00:00Z",
        certificate_number="SC-2026-000001",
    )
    out = session_out_from_rows(session_row, [])
    assert out.status is SessionStatus.ISSUED
    assert out.submitted_at == "2026-01-02T00:00:00Z"
    assert out.approved_by == "user-approver"
    assert out.approved_at == "2026-01-03T00:00:00Z"
    assert out.issued_at == "2026-01-04T00:00:00Z"
    assert out.certificate_number == "SC-2026-000001"


def test_session_out_from_rows_accepts_an_explicit_return_reason():
    # return_reason is NOT a test_sessions column — the caller (the router)
    # passes it in explicitly, derived from audit_log.
    session_row = dict(
        id="sess-1",
        instrument_id="instr-1",
        verification_type="initial",
        status="returned",
        created_by="user-123",
        created_at="2026-01-01T00:00:00Z",
    )
    out = session_out_from_rows(session_row, [], return_reason="missing environmental conditions")
    assert out.return_reason == "missing environmental conditions"


def test_session_return_in_requires_a_non_empty_reason():
    with pytest.raises(ValidationError):
        SessionReturnIn(reason="")


def test_session_return_in_accepts_a_reason():
    payload = SessionReturnIn(reason="Please re-check load #4")
    assert payload.reason == "Please re-check load #4"
