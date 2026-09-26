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
