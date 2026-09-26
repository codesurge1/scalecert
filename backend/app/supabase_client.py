"""Supabase client factories.

Only two factories exist here, on purpose: an anon client (no user context) and a
per-request user-scoped client built from the caller's JWT. There is deliberately
no service-role client in this module — service-role is for privileged system
tasks only (CLAUDE.md), and this task has no such task yet. Adding one back
requires a reason, not a convenience import.

NOTE: DATABASE_URL is the transaction-mode pooler; used by later direct-DB tasks,
not here. All reads in this task go through supabase-py (PostgREST), which is
what carries RLS.
"""

import os

from supabase import Client, create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]


def anon_client() -> Client:
    """A Supabase client with no user context (anon key only, no auth header)."""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def user_client(access_token: str) -> Client:
    """A Supabase client scoped to the caller's identity via their JWT.

    This is the ONLY path for user-scoped reads/writes — it makes PostgREST send
    the caller's `Authorization: Bearer <token>`, so RLS policies evaluate
    `auth.uid()` as that user. Never use the service-role key for this purpose.
    """
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(access_token)
    return client
