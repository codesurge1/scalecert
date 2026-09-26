"""Thin, mockable DB-IO wrappers — each function takes a Supabase `Client`
(already user-scoped by app.deps.get_auth_context, so RLS applies) plus plain
arguments, and does exactly one `.table(...).select/insert/delete(...)
.execute()` call. No business logic lives here — that's services/; no
routing lives here — that's routers/. Kept this thin specifically so routers
can be tested against a fake client (see backend/tests/) without a live
Supabase connection.
"""
