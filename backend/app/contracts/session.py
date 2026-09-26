"""Pydantic v2 contracts for `test_sessions` / `session_test_selection` (a
resource contract, not a test_type contract — see app/contracts/__init__.py).
"""

from typing import Optional

from pydantic import UUID4, BaseModel, ConfigDict

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
    test_selections: list[SessionTestSelectionOut] = []


def session_insert_payload(created_by: str, payload: SessionIn) -> dict:
    """SessionIn -> the dict handed to `.table("test_sessions").insert()`.
    `status` is left out — the column's own `default 'draft'` is the single
    source of truth for a new session's starting status.
    """
    data = payload.model_dump(mode="json")
    data["created_by"] = created_by
    return data


def session_out_from_rows(session_row: dict, selection_rows: list[dict]) -> SessionOut:
    return SessionOut(
        id=session_row["id"],
        instrument_id=session_row["instrument_id"],
        verification_type=session_row["verification_type"],
        status=session_row["status"],
        created_by=session_row["created_by"],
        created_at=session_row["created_at"],
        test_selections=[SessionTestSelectionOut(**row) for row in selection_rows],
    )
