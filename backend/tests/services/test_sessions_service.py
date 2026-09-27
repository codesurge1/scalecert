"""Pure unit tests for app.services.sessions — no DB, no HTTP."""

import pytest

from app.contracts.common import SessionStatus
from app.services.sessions import (
    CannotActOnOwnSession,
    CannotIssue,
    InvalidTransition,
    NotAnApprover,
    NotSessionCreator,
    SessionHasNoReadings,
    SessionNotDraft,
    ensure_can_issue,
    ensure_has_readings,
    ensure_is_approver_or_admin,
    ensure_is_creator,
    ensure_not_own_session,
    ensure_session_is_draft,
    ensure_status,
)


def test_ensure_session_is_draft_passes_for_draft():
    ensure_session_is_draft(SessionStatus.DRAFT)  # must not raise


@pytest.mark.parametrize(
    "status",
    [
        SessionStatus.SUBMITTED,
        SessionStatus.RETURNED,
        SessionStatus.APPROVED,
        SessionStatus.ISSUED,
        SessionStatus.SUPERSEDED,
    ],
)
def test_ensure_session_is_draft_rejects_every_other_status(status):
    with pytest.raises(SessionNotDraft):
        ensure_session_is_draft(status)


# ---------------------------------------------------------------------------
# ensure_status — the out-of-order-transition guard (-> 409 at the router).
# ---------------------------------------------------------------------------
def test_ensure_status_passes_when_current_matches_expected():
    ensure_status(SessionStatus.SUBMITTED, SessionStatus.SUBMITTED, "approve this session")  # must not raise


@pytest.mark.parametrize(
    "current,expected",
    [
        (SessionStatus.DRAFT, SessionStatus.SUBMITTED),  # approve a draft
        (SessionStatus.DRAFT, SessionStatus.APPROVED),  # issue a draft
        (SessionStatus.APPROVED, SessionStatus.SUBMITTED),  # approve an already-approved session
        (SessionStatus.ISSUED, SessionStatus.APPROVED),  # issue an already-issued session
    ],
)
def test_ensure_status_rejects_every_out_of_order_move(current, expected):
    with pytest.raises(InvalidTransition) as excinfo:
        ensure_status(current, expected, "do this")
    message = str(excinfo.value)
    assert current.value in message
    assert expected.value in message


# ---------------------------------------------------------------------------
# ensure_is_creator / ensure_is_approver_or_admin / ensure_not_own_session —
# the API-layer defense-in-depth checks, independent of RLS.
# ---------------------------------------------------------------------------
def test_ensure_is_creator_passes_for_the_creator():
    ensure_is_creator("user-1", "user-1", "submit")  # must not raise


def test_ensure_is_creator_rejects_a_different_user():
    with pytest.raises(NotSessionCreator):
        ensure_is_creator("user-1", "user-2", "submit")


@pytest.mark.parametrize("role", ["approver", "admin"])
def test_ensure_is_approver_or_admin_passes_for_either_role(role):
    ensure_is_approver_or_admin(role, "approve")  # must not raise


@pytest.mark.parametrize("role", ["technician", None])
def test_ensure_is_approver_or_admin_rejects_technician_and_missing_role(role):
    with pytest.raises(NotAnApprover):
        ensure_is_approver_or_admin(role, "approve")


def test_ensure_not_own_session_passes_when_different_users():
    ensure_not_own_session("user-1", "user-2", "approve")  # must not raise


def test_ensure_not_own_session_rejects_the_separation_of_duties_violation():
    # The core scenario this whole task exists to demonstrate: an approver
    # attempting to approve/return/issue a session THEY THEMSELVES created.
    with pytest.raises(CannotActOnOwnSession) as excinfo:
        ensure_not_own_session("user-1", "user-1", "approve")
    assert "separation of duties" in str(excinfo.value)


# ---------------------------------------------------------------------------
# ensure_can_issue — admin issues anything approved; an approver issues only
# the session they themselves approved.
# ---------------------------------------------------------------------------
def test_ensure_can_issue_passes_for_admin_regardless_of_who_approved():
    ensure_can_issue("admin", "user-admin", "user-approver-a")  # must not raise


def test_ensure_can_issue_passes_for_the_same_approver_who_approved():
    ensure_can_issue("approver", "user-approver-a", "user-approver-a")  # must not raise


def test_ensure_can_issue_rejects_a_different_approver():
    with pytest.raises(CannotIssue):
        ensure_can_issue("approver", "user-approver-b", "user-approver-a")


def test_ensure_can_issue_rejects_when_approved_by_is_missing():
    with pytest.raises(CannotIssue):
        ensure_can_issue("approver", "user-approver-a", None)


# ---------------------------------------------------------------------------
# ensure_has_readings — a session with zero readings shouldn't be submittable.
# ---------------------------------------------------------------------------
def test_ensure_has_readings_passes_when_true():
    ensure_has_readings(True)  # must not raise


def test_ensure_has_readings_rejects_when_false():
    with pytest.raises(SessionHasNoReadings):
        ensure_has_readings(False)
