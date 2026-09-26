from supabase import Client

from app.repositories.errors import run_insert, run_select

READINGS_TABLE = "test_readings"
RESULTS_TABLE = "test_results"
AUDIT_TABLE = "audit_log"


def insert_reading(
    client: Client,
    *,
    session_id: str,
    entered_by: str,
    sequence_no: int,
    direction: str,
    data: dict,
) -> dict:
    return run_insert(
        client.table(READINGS_TABLE).insert(
            {
                "session_id": session_id,
                "test_type": "weighing",
                "sequence_no": sequence_no,
                "direction": direction,
                "data": data,
                "entered_by": entered_by,
            }
        ),
        table=READINGS_TABLE,
        hint=(
            "recording a reading — check policy 'readings_write' (requires entered_by = caller and "
            "a visible, own, draft-status session)"
        ),
    )


def list_readings(client: Client, *, session_id: str, test_type: str) -> list[dict]:
    # Ordered by created_at so the router can do last-write-wins dedup on
    # (sequence_no, direction) if a direction was ever resubmitted — there's
    # no update endpoint, so a resubmission is a second insert, not an
    # overwrite (docs/architecture.md).
    return run_select(
        client.table(READINGS_TABLE).select("*").eq("session_id", session_id).eq("test_type", test_type).order("created_at"),
        table=READINGS_TABLE,
        hint=f"listing readings for session {session_id!r}",
    )


def list_results(client: Client, *, session_id: str, test_type: str) -> list[dict]:
    return run_select(
        client.table(RESULTS_TABLE).select("*").eq("session_id", session_id).eq("test_type", test_type),
        table=RESULTS_TABLE,
        hint=f"listing results for session {session_id!r}",
    )


def delete_reading(client: Client, reading_id: str) -> None:
    client.table(READINGS_TABLE).delete().eq("id", reading_id).execute()


def insert_result(client: Client, *, session_id: str, reading_id: str, result: dict, passed: bool) -> dict:
    return run_insert(
        client.table(RESULTS_TABLE).insert(
            {
                "session_id": session_id,
                "test_type": "weighing",
                "reading_id": reading_id,
                "result": result,
                "passed": passed,
            }
        ),
        table=RESULTS_TABLE,
        hint="recording a result — check policy 'results_write' (requires a visible, own, draft-status session)",
    )


def insert_audit_log(client: Client, *, session_id: str, actor_id: str, action: str, data: dict) -> None:
    client.table(AUDIT_TABLE).insert(
        {"session_id": session_id, "actor_id": actor_id, "action": action, "data": data}
    ).execute()
