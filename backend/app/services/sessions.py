"""Pure session-state business rules. No DB, no HTTP — unit-testable directly."""

from app.contracts.common import SessionStatus


class SessionNotDraft(ValueError):
    """Raised when an operation that requires status == 'draft' is attempted
    on a session in any other status (e.g. submitting a reading)."""


def ensure_session_is_draft(status: SessionStatus) -> None:
    """Readings are only accepted while a session is `draft` (CLAUDE.md /
    docs/plan.md Phase 2). `returned -> draft` reopening and the
    `submitted`/`approved`/`issued` transitions are a later task's concern —
    this function deliberately only enforces the one rule this task owns,
    so reopening later is a matter of moving a session back to `draft`, not
    of relaxing this check.
    """
    if status is not SessionStatus.DRAFT:
        raise SessionNotDraft(f"session status is {status.value!r}, not 'draft' — readings are not accepted")
