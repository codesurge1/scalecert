from supabase import Client

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
    rows = (
        client.table(READINGS_TABLE)
        .insert(
            {
                "session_id": session_id,
                "test_type": "weighing",
                "sequence_no": sequence_no,
                "direction": direction,
                "data": data,
                "entered_by": entered_by,
            }
        )
        .execute()
        .data
    )
    return rows[0]


def list_readings(client: Client, *, session_id: str, test_type: str) -> list[dict]:
    # Ordered by created_at so the router can do last-write-wins dedup on
    # (sequence_no, direction) if a direction was ever resubmitted — there's
    # no update endpoint, so a resubmission is a second insert, not an
    # overwrite (docs/architecture.md).
    return (
        client.table(READINGS_TABLE)
        .select("*")
        .eq("session_id", session_id)
        .eq("test_type", test_type)
        .order("created_at")
        .execute()
        .data
    )


def list_results(client: Client, *, session_id: str, test_type: str) -> list[dict]:
    return (
        client.table(RESULTS_TABLE)
        .select("*")
        .eq("session_id", session_id)
        .eq("test_type", test_type)
        .execute()
        .data
    )


def delete_reading(client: Client, reading_id: str) -> None:
    client.table(READINGS_TABLE).delete().eq("id", reading_id).execute()


def insert_result(client: Client, *, session_id: str, reading_id: str, result: dict, passed: bool) -> dict:
    rows = (
        client.table(RESULTS_TABLE)
        .insert(
            {
                "session_id": session_id,
                "test_type": "weighing",
                "reading_id": reading_id,
                "result": result,
                "passed": passed,
            }
        )
        .execute()
        .data
    )
    return rows[0]


def insert_audit_log(client: Client, *, session_id: str, actor_id: str, action: str, data: dict) -> None:
    client.table(AUDIT_TABLE).insert(
        {"session_id": session_id, "actor_id": actor_id, "action": action, "data": data}
    ).execute()
