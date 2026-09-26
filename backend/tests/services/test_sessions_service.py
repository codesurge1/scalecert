"""Pure unit tests for app.services.sessions — no DB, no HTTP."""

import pytest

from app.contracts.common import SessionStatus
from app.services.sessions import SessionNotDraft, ensure_session_is_draft


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
