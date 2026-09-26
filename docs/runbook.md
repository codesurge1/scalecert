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

Backend (`cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`) on `http://localhost:8000`, routes under `/api`. Frontend (`cd frontend && npm install && npm run dev`) on `http://localhost:5173`. Full instructions and the RLS acceptance check: see [README.md](../README.md#running-the-walking-skeleton).

## Database migration & reset

To set up a fresh project:
1. Run `db/schema.sql` in the Supabase SQL editor.
2. Create the `reports` Storage bucket.
3. Create the technician and approver demo accounts via Supabase Auth.
4. Run `db/seed.sql` to promote the approver account.

To reset: drop and recreate the project (or its schema), then re-run `db/schema.sql` and `db/seed.sql`.

## Deploy (Vercel)

One project, one domain, two [Vercel Services](https://vercel.com/docs/services) defined in `/vercel.json` (repo root): `frontend` (Vite build, served at `/`) and `backend` (FastAPI, `backend/main.py` entrypoint shim, reachable under `/api`). Env vars are set in the Vercel dashboard, not committed anywhere — full list, and the post-deploy RLS acceptance check, are in [README.md](../README.md#deploying-to-vercel).

## Common issues
