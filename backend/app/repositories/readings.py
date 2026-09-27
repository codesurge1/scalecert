from typing import Optional

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
    test_type: str,
    sequence_no: int,
    direction: Optional[str] = None,
    series_no: Optional[int] = None,
    position_no: Optional[int] = None,
    run_id: Optional[str] = None,
    data: dict,
) -> dict:
    """`test_type` is required (no default) so every call site says
    explicitly which test it's writing for — `db/schema.sql`'s
    `test_readings` table is shared across all test_type values (the
    "hybrid design", docs/architecture.md), including 'weighing' covering
    both the full Weighing load sequence AND its zero/tare-device variant
    (distinguished from each other by `direction`: always set for a
    Weighing-sequence reading, always null for a zero/tare one — see
    app/contracts/zero_tare.py). `series_no`/`position_no` are Repeatability's
    and Eccentricity's own columns respectively; every other test type
    leaves them null. `run_id` (feat/test-runs-conditions) is null unless
    the caller is submitting against an explicitly created run — the
    default/only run of any test is null, exactly as before this column
    existed.
    """
    return run_insert(
        client.table(READINGS_TABLE).insert(
            {
                "session_id": session_id,
                "test_type": test_type,
                "sequence_no": sequence_no,
                "direction": direction,
                "series_no": series_no,
                "position_no": position_no,
                "run_id": run_id,
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


def has_any_reading(client: Client, *, session_id: str) -> bool:
    """Whether at least one reading of ANY test_type has been recorded for
    this session — used by the submit lifecycle transition (a session with
    zero readings shouldn't be submittable for review). Deliberately no
    test_type filter, unlike list_readings: this check spans all seven
    checklist tests, not one."""
    rows = run_select(
        client.table(READINGS_TABLE).select("id").eq("session_id", session_id).limit(1),
        table=READINGS_TABLE,
        hint=f"checking whether session {session_id!r} has any recorded reading",
    )
    return bool(rows)


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


def insert_result(
    client: Client,
    *,
    session_id: str,
    test_type: str,
    reading_id: str,
    result: dict,
    passed: bool,
    run_id: Optional[str] = None,
) -> dict:
    return run_insert(
        client.table(RESULTS_TABLE).insert(
            {
                "session_id": session_id,
                "test_type": test_type,
                "reading_id": reading_id,
                "run_id": run_id,
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
