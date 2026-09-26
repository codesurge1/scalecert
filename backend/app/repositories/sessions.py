from supabase import Client

from app.contracts.session import SessionIn, session_insert_payload
from app.repositories.errors import run_insert, run_select

SESSIONS_TABLE = "test_sessions"
SELECTIONS_TABLE = "session_test_selection"


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
