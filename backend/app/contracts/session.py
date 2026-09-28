"""Pydantic v2 contracts for `test_sessions` / `session_test_selection` (a
resource contract, not a test_type contract — see app/contracts/__init__.py).
"""

from typing import Optional

from pydantic import UUID4, BaseModel, ConfigDict, Field

from app.contracts.common import SessionStatus, TestType
from engine.types import VerificationType


class SessionIn(BaseModel):
    """What a client submits to open a Weighing session for an instrument."""

    model_config = ConfigDict(extra="forbid")

    # UUID4-typed (not a bare `str`) so a malformed/empty/"undefined" id —
    # the frontend-bug shape that used to reach Postgres as a raw string and
    # 500 on "invalid input syntax for type uuid" — fails Pydantic
    # validation instead, as a clean 422, before any DB call happens.
    # `instruments.id` is `gen_random_uuid()` (pgcrypto), always a v4 UUID.
    instrument_id: UUID4
    verification_type: VerificationType


class SessionReturnIn(BaseModel):
    """What an approver submits to `POST /sessions/{id}/return`. `reason` is
    required and non-empty — a return with no explanation would leave the
    technician with nothing to act on, so this is enforced here (a clean
    422) rather than left to the DB (which has no dedicated column for it
    at all — see app/repositories/sessions.get_latest_return_reason)."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)


class SessionTestSelectionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    test_type: TestType
    applicable: bool
    na_reason: Optional[str] = None
    zero_device_status: Optional[str] = None
    status: str


class SessionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    instrument_id: str
    verification_type: VerificationType
    status: SessionStatus
    created_by: str
    created_at: str
    # Lifecycle trail (this task) — all None until the corresponding
    # transition happens. Timestamps are plain strings, same convention as
    # `created_at` above (never parsed into a datetime here).
    submitted_at: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    issued_at: Optional[str] = None
    certificate_number: Optional[str] = None
    # Set once a certificate PDF has actually been generated and uploaded —
    # `null` until then, including for an issued session where generation
    # failed or hasn't happened yet (fix/certificate-generation-wiring: the
    # download affordance never gates on this being set, it's informational
    # only — see SessionLifecyclePanel.jsx).
    report_storage_path: Optional[str] = None
    # NOT a `test_sessions` column, NEVER persisted — set only by
    # `issue_session`'s own response (app/routers/sessions.py) when its
    # best-effort certificate generation fails, so the caller sees it ONCE,
    # on the response to the action that triggered it; absent (None) on
    # every other read of this session, including a moment later.
    report_generation_error: Optional[str] = None
    # NOT a `test_sessions` column — derived from the latest `action='returned'`
    # audit_log row for this session (see
    # app.repositories.sessions.get_latest_return_reason); populated by the
    # caller only when it's actually relevant (status == 'returned').
    return_reason: Optional[str] = None
    test_selections: list[SessionTestSelectionOut] = []


def session_insert_payload(created_by: str, payload: SessionIn) -> dict:
    """SessionIn -> the dict handed to `.table("test_sessions").insert()`.
    `status` is left out — the column's own `default 'draft'` is the single
    source of truth for a new session's starting status.
    """
    data = payload.model_dump(mode="json")
    data["created_by"] = created_by
    return data


def session_out_from_rows(
    session_row: dict, selection_rows: list[dict], *, return_reason: Optional[str] = None
) -> SessionOut:
    return SessionOut(
        id=session_row["id"],
        instrument_id=session_row["instrument_id"],
        verification_type=session_row["verification_type"],
        status=session_row["status"],
        created_by=session_row["created_by"],
        created_at=session_row["created_at"],
        submitted_at=session_row.get("submitted_at"),
        approved_by=session_row.get("approved_by"),
        approved_at=session_row.get("approved_at"),
        issued_at=session_row.get("issued_at"),
        certificate_number=session_row.get("certificate_number"),
        report_storage_path=session_row.get("report_storage_path"),
        return_reason=return_reason,
        test_selections=[SessionTestSelectionOut(**row) for row in selection_rows],
    )
