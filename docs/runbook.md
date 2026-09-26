# Runbook

Purpose: describe local setup, environment configuration, and deployment for ScaleCert.

> STATUS: skeleton — to be populated in a later prompt. Do not treat as authoritative yet.

## Prerequisites

## Environment variables

Keys from `.env.example`:
- `SUPABASE_URL` — the Supabase project URL.
- `SUPABASE_ANON_KEY` — public anon key; safe for client use, subject to RLS.
- `SUPABASE_SERVICE_ROLE_KEY` — backend only; never for user-scoped queries.
- `DATABASE_URL` — POOLED connection string (Supavisor, transaction mode), not the direct connection.
- `SUPABASE_STORAGE_BUCKET=reports` — Storage bucket for generated PDF certificates/reports.

## Local setup

## Database migration & reset

To set up a fresh project:
1. Run `db/schema.sql` in the Supabase SQL editor.
2. Create the `reports` Storage bucket.
3. Create the technician and approver demo accounts via Supabase Auth.
4. Run `db/seed.sql` to promote the approver account.

To reset: drop and recreate the project (or its schema), then re-run `db/schema.sql` and `db/seed.sql`.

## Deploy (Vercel)

## Common issues
