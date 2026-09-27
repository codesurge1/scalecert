from typing import Optional

from supabase import Client

from app.repositories.errors import run_select

PROFILES_TABLE = "profiles"


def get_role(client: Client, user_id: str) -> Optional[str]:
    """The CALLER's own role — reliable only when `user_id` is the caller's
    own id, since `profiles_select_own`'s `id = auth.uid()` clause is what
    guarantees this row is visible regardless of role (the same clause
    `/whoami` already relies on). Used by the lifecycle-transition routes to
    decide whether the caller may act as an approver/admin — a defense-in-
    depth check alongside RLS's own `sessions_update_approver` role clause,
    so a non-approver gets a clean 403 with a specific message rather than
    a generic RLS rejection.
    """
    rows = run_select(
        client.table(PROFILES_TABLE).select("id, role").eq("id", user_id),
        table=PROFILES_TABLE,
        hint=f"fetching role for user {user_id!r} — check policy 'profiles_select_own'",
    )
    return rows[0]["role"] if rows else None
