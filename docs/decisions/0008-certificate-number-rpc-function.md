# 0008 — A small SECURITY DEFINER function to consume `certificate_number_seq`

## Status

Accepted

## Context

This task (session lifecycle: submit → approve/return → issue) needs to assign a certificate number — `SC-{YEAR}-{6-digit sequential}`, drawn from the existing `certificate_number_seq` sequence (`db/schema.sql`, present since ADR-0005) — at the moment a session is issued. CLAUDE.md and docs/architecture.md are explicit that this format and this sequence are the source of truth.

The backend never uses the Supabase service-role key for user-scoped writes (CLAUDE.md) — every write goes through a per-request, JWT-scoped client, so RLS applies as the caller. That client talks to Postgres only through PostgREST's REST surface: table CRUD, or a call to a Postgres function already exposed via `rpc/`. PostgREST has no endpoint for calling `nextval()` on a bare sequence directly — there is no way to atomically consume `certificate_number_seq` from application code without either (a) a stored function, or (b) computing a number in Python without a real sequence (racy across concurrent approvers, and not actually "from `certificate_number_seq`" as required).

## Decision

Add one small `SECURITY DEFINER` SQL function, `public.issue_certificate_number()`, to `db/schema.sql`, right alongside the two existing functions (`get_my_role`, `handle_new_user`) it already has. It does exactly three things: checks the caller's role via `get_my_role()` (raises `42501` if not `approver`/`admin` — the same error code RLS's own separation-of-duties rejection already uses, so it's caught by the same `_is_rls_error` check the rest of the app uses), calls `nextval('certificate_number_seq')`, and formats the result as `SC-{YEAR}-{6-digit}`. Called via `client.rpc("issue_certificate_number", {})` from the JWT-scoped client — never the service-role key. `GRANT EXECUTE ... TO authenticated` so any signed-in user can call it, with the function's own role check doing the real gating (the same "coarse DB guard, precise API/DB-function check" split the rest of this app's RLS already uses).

This is the one, narrow exception to "don't change the schema" in this task's own scope note: the columns it needs already existed, but the *plumbing* to consume a Postgres sequence from a REST-only client did not, and cannot exist without a stored function. No table, column, or RLS policy changes.

## Consequences

- Certificate numbers are genuinely atomic and gap-tolerant, matching how Postgres sequences are meant to be used — exactly the guarantee CLAUDE.md's "Postgres sequence" requirement calls for, which pure application-side counting could not provide.
- A wasted/skipped sequence number is possible if `issue_certificate_number()` succeeds but the subsequent `test_sessions` UPDATE (setting `status='issued'`) then fails for an unrelated reason (e.g. a transient network error) — `nextval()` is never rolled back by a failed later statement, by design. This is the accepted, standard behavior of Postgres sequences (gaps are always possible, e.g. on any rolled-back transaction) and is called out explicitly in `app/repositories/sessions.py`'s docstring rather than treated as a bug to fix.
- The role check lives in two places now (RLS's own policies, and this function) — duplication, but deliberate: RLS's `sessions_update_approver` policy has no way to gate an RPC call, which isn't a table operation at all, so the function needs its own equivalent check to avoid becoming an unguarded technician-callable endpoint.
- `CREATE OR REPLACE FUNCTION` + `GRANT EXECUTE` is idempotent and non-destructive — an operator can run just this block directly against an already-provisioned live project (no reset, no `db/migrations/` file needed, unlike ADR-0007's column-addition case) to bring it up to date.
