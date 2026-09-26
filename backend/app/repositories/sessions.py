from supabase import Client

from app.contracts.session import SessionIn, session_insert_payload

SESSIONS_TABLE = "test_sessions"
SELECTIONS_TABLE = "session_test_selection"


def insert_session(client: Client, created_by: str, payload: SessionIn) -> dict:
    data = session_insert_payload(created_by, payload)
    rows = client.table(SESSIONS_TABLE).insert(data).execute().data
    return rows[0]


def get_session(client: Client, session_id: str) -> dict | None:
    rows = client.table(SESSIONS_TABLE).select("*").eq("id", session_id).execute().data
    return rows[0] if rows else None


def insert_session_test_selection(client: Client, session_id: str, test_type: str) -> dict:
    rows = (
        client.table(SELECTIONS_TABLE)
        .insert({"session_id": session_id, "test_type": test_type, "applicable": True})
        .execute()
        .data
    )
    return rows[0]


def get_session_test_selections(client: Client, session_id: str) -> list[dict]:
    return client.table(SELECTIONS_TABLE).select("*").eq("session_id", session_id).execute().data
