# 0009 — Two narrow SECURITY DEFINER exceptions: public verify, and setting `report_storage_path` on an issued session

## Status

Accepted

## Context

This task (PDF certificate generation + public verification) needs two things the existing schema and RLS policy set cannot do:

1. **A public, login-free lookup.** `GET /verify/{certificate_number}` must work for anyone — no Supabase session, no JWT. Every RLS policy in this schema requires `auth.uid()` to resolve to something (a role, a `created_by` match, ...); there is deliberately no anonymous-read policy anywhere (correctly — nothing else here should be publicly queryable). An anonymous caller therefore cannot SELECT `test_sessions`/`instruments` at all, under any existing policy.
2. **Recording where the generated PDF was stored, on an already-issued session.** `test_sessions.report_storage_path` needs to be set once the certificate PDF is generated (`POST /sessions/{id}/report`), but that only happens *after* a session reaches `issued`. Per the session lifecycle (ADR-0008, docs/architecture.md), an `issued` row matches **no** UPDATE policy on `test_sessions` at all — `sessions_update_owner` requires status in `draft`/`returned`→`draft`/`submitted`, `sessions_update_approver` requires status in `submitted`/`returned`/`approved`. This is deliberate: an issued certificate's content must never be alterable. A plain `.update()` from any role, including admin, is rejected by RLS 100% of the time on an issued row.

## Decision

Two small `SECURITY DEFINER` Postgres functions, following the exact precedent ADR-0008 already set with `issue_certificate_number()`: each does its OWN authorization check internally (since it runs as the function owner, bypassing the caller's own RLS visibility), and each is scoped as narrowly as possible to the one thing it exists for.

**`public.get_public_certificate_info(p_certificate_number text)`** — `STABLE`, returns a `TABLE` of exactly: `certificate_number`, `status`, `instrument_model`, `instrument_manufacturer`, `instrument_type_designation`, `accuracy_class`, `verification_type`, `issued_at`. Its own `WHERE` clause requires `status = 'issued'` — a certificate number that doesn't exist, or exists but belongs to a `draft`/`submitted`/`approved`/`returned`/`superseded` session, comes back as **zero rows**, indistinguishably. `GRANT EXECUTE ... TO anon, authenticated` — this is the ONE deliberate anonymous-read exception in the whole schema. It is safe specifically because of what it returns, not because of who can call it: the anon key alone grants no ability to query any table directly (RLS still blocks that completely); it can only invoke this one function, and the function itself decides the entire safe field list and the `issued`-only gate. Never returns technician/approver identity, raw readings, internal ids, or remarks — those columns are never even in the `SELECT` list, so there is no field to accidentally leak later by loosening a filter.

**`public.set_report_storage_path(p_session_id uuid, p_path text)`** — `RETURNS void`, checks (in order): the session exists; its status is `issued` (else `RAISE EXCEPTION ... ERRCODE '42501'`); the caller is the session's own creator OR has role `approver`/`admin` (else the same `42501`) — then updates ONLY `report_storage_path` on that one row. This does not reopen general mutability of an issued session: the function has no parameter and no code path that could touch `status`, `certificate_number`, `approved_by`, or any other column; a caller who passes a `session_id` for a `draft` session gets rejected, not a partial write.

Both functions reuse `public.get_my_role()` (already `SECURITY DEFINER`, from the original schema) for their role checks, and both raise Postgres error code `42501` (`insufficient_privilege`) on a rejection — the same code RLS itself raises, so `app.repositories.errors._is_rls_error` classifies a rejection from either function exactly like a genuine RLS rejection (403, not 500), with no special-casing needed at the Python layer.

## Consequences

- The public verify surface (`app/routers/verify.py`) never touches a per-request user-scoped client at all — it uses `app.supabase_client.anon_client()` (which already existed, unused, before this task) for every call. This is a genuine, narrow exception to CLAUDE.md's usual "every request that reads/writes a user's data uses a per-request, user-scoped client" rule — justified because there IS no user on this path, by design, and the exception is bounded to exactly one function call per route, never a broader anonymous table access.
- `report_storage_path` becomes the one column on `test_sessions` settable after `issued`, via exactly one function, with its own authorization check duplicating (as defense in depth, same philosophy as every other write in this app) what the API layer already checks before calling it.
- A discrepancy report writes through a third path: not a function, but a single-purpose RLS policy (`discrepancy_insert_anon on discrepancy_reports for insert with check (true)`) — simpler than a function for a plain, unconditional insert, and it grants nothing beyond that one table/one operation (there is no matching anonymous SELECT policy, so a report can never be read back except by an admin).
- Any future column added to `get_public_certificate_info()`'s return list is a new, deliberate decision each time — it is not a view or a `SELECT *`, so nothing is exposed by accident as the schema evolves. The same discipline applies to `set_report_storage_path`: it must never grow a second settable column without equally deliberate reasoning.
