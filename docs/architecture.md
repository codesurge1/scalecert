# Architecture

Purpose: describe the system's structure — schema, engine, roles, API surface — as the single source of truth for how ScaleCert is built.

> STATUS: schema, roles, and session lifecycle are authoritative as of ADR-0005. Engine, API, PDF, and audit sections are pending their build tasks.

## System overview

## Scope (the 7 tests)

## Tech stack

## Database schema

`db/schema.sql` is the single source of truth for the database (ADR-0002, ADR-0005) — never dashboard clicks.

Seven tables:
- **profiles** — one row per `auth.users` row, holds `role` (technician/approver/admin) and `full_name`. Created by `handle_new_user()` on signup.
- **instruments** — the registered NAWI: accuracy class, `e_value`/`d_value`, Max/Min capacity, indication type, and the `is_mobile`/`is_multi_interval` flags that gate the conditional tests.
- **test_sessions** — one verification session per instrument visit: status, certificate number, approval trail, and the report-header patch fields (see below).
- **session_test_selection** — which of the six `test_type`s apply to this session, with an NA reason where they don't and a per-test `zero_device_status`.
- **test_readings** — raw technician input per test, one row per reading (or per series/position where applicable), keyed by `test_type`.
- **test_results** — computed verdicts derived from readings, keyed by `test_type` and optionally `reading_id`.
- **audit_log** — append-only record of actions taken against a session.

Enums: `user_role`, `accuracy_class`, `verification_type`, `session_status`, `indication_type`, `test_type`.

**Hybrid design.** `test_readings` and `test_results` are each a single table across all six `test_type`s, not one table per test. Test-type-specific fields live in a `data` / `result` JSONB column; the shape of that JSON is enforced by a Pydantic model per `test_type` at the API layer, not by the database. This keeps the schema stable as test-specific fields evolve, at the cost of the DB not being able to validate that shape itself.

**Report-header patches.** Four fields were added to `test_sessions` from the RRSL visit (Part D.3): `observer_name`, `test_date`, `environmental_conditions` (start/max/end × Temp/Rel.h/Time/Bar.pres, JSONB), and `remarks`. A fifth patch, `zero_device_status`, lives on `session_test_selection` instead, since it's per-test rather than per-session.

**Resolution during test.** The report form's "resolution during test" field is not its own column — it renders as `COALESCE(d_value, e_value)` from `instruments`.

**Certificate numbering.** `certificate_number` on `test_sessions` is assigned only at approval time, formatted `SC-{YEAR}-{6-digit sequential}` drawn from `certificate_number_seq` — never before approval (see CLAUDE.md guardrails).

## Engine design

## Roles & permissions

Three roles: `technician`, `approver`, `admin`. New signups default to `technician` via `handle_new_user()`; promotion to `approver`/`admin` is seed-script-only (ADR-0004), not an admin UI.

The non-negotiable rule is separation of duties: no one both produces and approves the same result. This is enforced twice:
- **At the database**, via RLS: the `sessions_update_approver` policy requires `created_by <> auth.uid()` in addition to the approver/admin role. A technician attempting to approve their own session matches no UPDATE policy at all and the write fails with Postgres error `42501`.
- **At the API layer**, as defense in depth, independent of the RLS check.

## Session lifecycle

`draft → submitted → approved → issued`, with two additional states:
- **returned** — an approver sends a submitted session back; the technician edits it from `draft` or `returned` and resubmits.
- **superseded** — an issued report later found to be wrong is never edited in place. A new session is created referencing the original via `supersedes_session_id`; the original session remains retrievable, not deleted.

`issued` sessions are immutable at the database: no UPDATE policy on `test_sessions` matches a row once its status is `issued`, so no role (including admin, under the current policy set) can modify it through RLS.

## API surface

## PDF & audit

## Out of scope

- Audit hash-chain columns (prev_hash/this_hash) are deferred (ADR-0005); the `data` column is present now, and the chain is stretch scope.
