from typing import Optional

from supabase import Client

from app.contracts.session import SessionIn, session_insert_payload
from app.repositories.errors import run_insert, run_rpc, run_rpc_void, run_select, run_update

SESSIONS_TABLE = "test_sessions"
SELECTIONS_TABLE = "session_test_selection"
AUDIT_TABLE = "audit_log"
CERTIFICATE_SEQUENCE = "certificate_number_seq"


def insert_session(client: Client, created_by: str, payload: SessionIn) -> dict:
    data = session_insert_payload(created_by, payload)
    return run_insert(
        client.table(SESSIONS_TABLE).insert(data),
        table=SESSIONS_TABLE,
        hint="creating a session — check policy 'sessions_insert_own' (created_by must equal the caller)",
    )


def get_session(client: Client, session_id: str) -> dict | None:
    rows = run_select(
        client.table(SESSIONS_TABLE).select("*").eq("id", session_id),
        table=SESSIONS_TABLE,
        hint=f"fetching session {session_id!r} — id may be malformed, or check policy 'sessions_select'",
    )
    return rows[0] if rows else None


def list_sessions_for_instrument(client: Client, instrument_id: str) -> list[dict]:
    return run_select(
        client.table(SESSIONS_TABLE).select("*").eq("instrument_id", instrument_id).order("created_at", desc=True),
        table=SESSIONS_TABLE,
        hint=f"listing sessions for instrument {instrument_id!r}",
    )


def insert_session_test_selection(client: Client, session_id: str, test_type: str) -> dict:
    return run_insert(
        client.table(SELECTIONS_TABLE).insert({"session_id": session_id, "test_type": test_type, "applicable": True}),
        table=SELECTIONS_TABLE,
        hint=(
            "adding a session_test_selection row — check policy 'sts_write' (requires a visible, "
            "own, draft-status test_sessions row for this session_id)"
        ),
    )


def get_session_test_selections(client: Client, session_id: str) -> list[dict]:
    return run_select(
        client.table(SELECTIONS_TABLE).select("*").eq("session_id", session_id),
        table=SELECTIONS_TABLE,
        hint=f"listing test selections for session {session_id!r}",
    )


def update_session(client: Client, session_id: str, patch: dict) -> dict:
    """The one write path for every lifecycle transition (submit/reopen/
    return/approve/issue) — a plain UPDATE of `patch`'s keys, gated by
    whichever of `sessions_update_owner`/`sessions_update_approver` matches
    the caller's role and the row's current status. Finer transition
    validity (e.g. rejecting an out-of-order move with a clean 409) is the
    caller's job (app/services/sessions.py) — this function only performs
    the write and translates both RLS failure shapes via `run_update`.
    """
    return run_update(
        client.table(SESSIONS_TABLE).update(patch).eq("id", session_id),
        table=SESSIONS_TABLE,
        hint=(
            f"updating session {session_id!r} (fields: {sorted(patch)}) — check policy "
            "'sessions_update_owner' or 'sessions_update_approver'"
        ),
    )


def get_latest_return_reason(client: Client, session_id: str) -> Optional[str]:
    """The reason text from the most recent `action='returned'` audit_log
    row for this session — the ONLY place a return reason is stored (no
    dedicated `test_sessions` column exists, and this task deliberately
    doesn't add one — see docs/architecture.md, Session lifecycle). Visible
    under the same RLS as the session itself (`audit_select`: creator,
    approver, or admin), so a technician viewing their own returned session
    can read it back.
    """
    rows = run_select(
        client.table(AUDIT_TABLE)
        .select("data")
        .eq("session_id", session_id)
        .eq("action", "returned")
        .order("created_at", desc=True)
        .limit(1),
        table=AUDIT_TABLE,
        hint=f"fetching the latest return reason for session {session_id!r}",
    )
    if not rows:
        return None
    return (rows[0].get("data") or {}).get("reason")


def issue_certificate_number(client: Client) -> str:
    """Calls the `issue_certificate_number()` Postgres function (db/schema.sql)
    to atomically consume `certificate_number_seq` and format the result as
    `SC-{YEAR}-{6-digit}`. A stored procedure is the only way to consume a
    sequence through PostgREST's table-only REST surface — see ADR-0008 for
    why this one small function was added rather than computing the number
    in application code (which could not be atomic across concurrent
    approvers without it).
    """
    return run_rpc(
        client.rpc("issue_certificate_number", {}),
        table=CERTIFICATE_SEQUENCE,
        hint="generating the next certificate number via issue_certificate_number()",
    )


def set_report_storage_path(client: Client, session_id: str, path: str) -> None:
    """Calls the `set_report_storage_path()` Postgres function (ADR-0009)
    to record where a generated certificate PDF was stored, on a session
    whose status is `issued`. A plain `.update()` cannot do this: once a
    session's status is `issued` it matches NO UPDATE policy on
    `test_sessions` at all (docs/architecture.md, Session lifecycle —
    "issued sessions are immutable at the database"), by design, for every
    OTHER column. This function is a narrow, purpose-built exception to
    exactly that immutability, scoped to this one column and re-checking
    the same creator-or-approver/admin authorization the API layer already
    enforces — it does not reopen general mutability of an issued session.
    """
    run_rpc_void(
        client.rpc("set_report_storage_path", {"p_session_id": session_id, "p_path": path}),
        table=SESSIONS_TABLE,
        hint=f"recording report_storage_path for session {session_id!r}",
    )
