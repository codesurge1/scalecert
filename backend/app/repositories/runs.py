from typing import Optional

from supabase import Client

from app.repositories.errors import run_insert, run_select

RUNS_TABLE = "test_runs"


def insert_run(
    client: Client,
    *,
    session_id: str,
    test_type: str,
    run_label: str,
    conditions: Optional[dict],
    ordinal: int,
    created_by: str,
) -> dict:
    return run_insert(
        client.table(RUNS_TABLE).insert(
            {
                "session_id": session_id,
                "test_type": test_type,
                "run_label": run_label,
                "conditions": conditions,
                "ordinal": ordinal,
                "created_by": created_by,
            }
        ),
        table=RUNS_TABLE,
        hint="recording a run — check policy 'runs_write' (requires a visible, own, draft-status session)",
    )


def list_runs(client: Client, *, session_id: str, test_type: str) -> list[dict]:
    return run_select(
        client.table(RUNS_TABLE).select("*").eq("session_id", session_id).eq("test_type", test_type).order("ordinal"),
        table=RUNS_TABLE,
        hint=f"listing runs for session {session_id!r}",
    )


def get_run(client: Client, run_id: str) -> Optional[dict]:
    rows = run_select(
        client.table(RUNS_TABLE).select("*").eq("id", run_id).limit(1),
        table=RUNS_TABLE,
        hint=f"looking up run {run_id!r}",
    )
    return rows[0] if rows else None
