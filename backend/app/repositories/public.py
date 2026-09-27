"""DB access for the PUBLIC, login-free verification surface
(app/routers/verify.py) — every call here uses the shared `anon_client()`
(app.supabase_client), never a per-request user-scoped client: there is no
user to scope to, by design, on this one deliberate, narrow exception to
CLAUDE.md's usual per-request-JWT rule (ADR-0009).

Safety here comes from WHAT is exposed, not from WHO is asking:
`get_public_certificate_info()` is a `SECURITY DEFINER` Postgres function
that itself enforces `status = 'issued'` and a fixed, hand-picked safe
field list (db/schema.sql) — the anon key alone grants no ability to
bypass RLS on any table; it can only call this one function, and that
function decides what comes back. `discrepancy_reports`' own RLS INSERT
policy (`with check (true)`, no matching SELECT for anon) is the ONLY
thing that permits the anonymous insert below, and it grants nothing else.
"""

from typing import Optional

from supabase import Client

from app.repositories.errors import run_insert, run_rpc_list

DISCREPANCY_TABLE = "discrepancy_reports"


def get_public_certificate_info(client: Client, certificate_number: str) -> Optional[dict]:
    """None for anything not found or not `issued` — the two cases are
    indistinguishable by design (the function's own WHERE clause filters
    both to zero rows), so a caller can never learn whether a non-issued
    session with this certificate_number exists."""
    rows = run_rpc_list(
        client.rpc("get_public_certificate_info", {"p_certificate_number": certificate_number}),
        table="test_sessions",
        hint=f"looking up public certificate info for {certificate_number!r}",
    )
    return rows[0] if rows else None


def insert_discrepancy_report(
    client: Client, *, certificate_number: str, description: str, contact: Optional[str]
) -> dict:
    return run_insert(
        client.table(DISCREPANCY_TABLE).insert(
            {"certificate_number": certificate_number, "description": description, "contact": contact}
        ),
        table=DISCREPANCY_TABLE,
        hint="recording a discrepancy report — check policy 'discrepancy_insert_anon'",
    )
