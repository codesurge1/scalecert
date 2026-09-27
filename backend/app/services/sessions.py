"""Pure session-state business rules. No DB, no HTTP — unit-testable directly."""

from typing import Optional

from app.contracts.common import SessionStatus


class SessionNotDraft(ValueError):
    """Raised when an operation that requires status == 'draft' is attempted
    on a session in any other status (e.g. submitting a reading)."""


def ensure_session_is_draft(status: SessionStatus) -> None:
    """Readings are only accepted while a session is `draft` (CLAUDE.md /
    docs/plan.md Phase 2). The `submitted`/`approved`/`issued` transitions
    and `returned -> draft` reopening are implemented below (this task) —
    this function still deliberately only enforces the one rule it always
    owned, so those transitions are a matter of moving a session back to
    `draft`, not of relaxing this check.
    """
    if status is not SessionStatus.DRAFT:
        raise SessionNotDraft(f"session status is {status.value!r}, not 'draft' — readings are not accepted")


# ---------------------------------------------------------------------------
# Lifecycle transitions: submit -> approve/return -> issue, with separation
# of duties. RLS (db/schema.sql: sessions_update_owner/sessions_update_approver)
# is the coarse, non-negotiable guard (a technician approving their own
# session matches no UPDATE policy at all -> 42501); everything below is the
# API-layer's OWN, finer-grained defense-in-depth check (CLAUDE.md:
# "Enforce at the database (RLS) AND the API layer"), so a rejection comes
# back as a specific, clean error instead of a generic RLS failure.
# ---------------------------------------------------------------------------


class InvalidTransition(ValueError):
    """Raised when a lifecycle transition is attempted from a status that
    doesn't allow it (e.g. approving a draft session, issuing a
    non-approved one) — always a 409 at the API layer, never a 500."""


class SessionHasNoReadings(ValueError):
    """Raised when submitting a session with zero readings recorded across
    every test — a session shouldn't move to 'submitted' with nothing yet
    to review."""


class NotSessionCreator(ValueError):
    """Raised when someone other than a session's own creator attempts a
    creator-only action (submit/reopen) — defense in depth alongside RLS's
    own `created_by = auth.uid()` clause in `sessions_update_owner`."""


class NotAnApprover(ValueError):
    """Raised when a non-approver/admin attempts an approver-only action
    (return/approve/issue) — defense in depth alongside RLS's own role
    clause in `sessions_update_approver`."""


class CannotActOnOwnSession(ValueError):
    """Raised by the API-layer separation-of-duties check — the same rule
    RLS's `created_by <> auth.uid()` clause enforces at the database, kept
    here too so an approver attempting to return/approve/issue their own
    session gets a clean, specific message instead of a bare RLS failure."""


class CannotIssue(ValueError):
    """Raised when the caller may not issue THIS session's certificate:
    only an admin, or the same approver who approved it, may do so (see
    docs/architecture.md, Session lifecycle, "Who issues" — a deliberate
    choice, not RLS-enforced, since RLS has no notion of "the same
    approver"; a different approver stepping in is a distinct decision from
    the original approval)."""


def ensure_status(current: SessionStatus, expected: SessionStatus, action: str) -> None:
    """The one status-precondition check every transition below uses."""
    if current is not expected:
        raise InvalidTransition(
            f"cannot {action}: session status is {current.value!r}, expected {expected.value!r}"
        )


def ensure_is_creator(created_by: str, actor_id: str, action: str) -> None:
    if created_by != actor_id:
        raise NotSessionCreator(f"cannot {action}: only the session's creator may do this")


def ensure_is_approver_or_admin(role: Optional[str], action: str) -> None:
    if role not in ("approver", "admin"):
        raise NotAnApprover(f"cannot {action}: only an approver or admin may do this")


def ensure_not_own_session(created_by: str, actor_id: str, action: str) -> None:
    if created_by == actor_id:
        raise CannotActOnOwnSession(
            f"cannot {action}: separation of duties — you cannot {action} a session you created yourself"
        )


def ensure_can_issue(role: Optional[str], actor_id: str, approved_by: Optional[str]) -> None:
    """Admin may issue any approved session; an approver may issue only the
    one they themselves approved — see `CannotIssue`."""
    if role == "admin":
        return
    if role == "approver" and approved_by is not None and approved_by == actor_id:
        return
    raise CannotIssue("only an admin, or the same approver who approved this session, may issue its certificate")


def ensure_has_readings(has_any_reading: bool) -> None:
    if not has_any_reading:
        raise SessionHasNoReadings(
            "cannot submit for review: no test has recorded any reading yet for this session"
        )
