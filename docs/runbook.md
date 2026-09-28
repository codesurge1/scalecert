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
- `PUBLIC_APP_BASE_URL` — **required** (`fix/certificate-generation-wiring`) — the public base URL a certificate's QR code encodes. Certificate generation (at issue time, and on-demand via "Download certificate") fails loudly with a clear error if this is unset, rather than silently falling back to the backend's own `request.base_url` — behind the two-service Vercel rewrite below, that fallback is not reliably the public-facing domain the browser actually used, and a silently wrong URL baked into an issued certificate's QR code is worse than refusing to generate one. Set it to this deployment's real public URL (e.g. `https://scalecert.example.com`), no trailing slash. Local dev: `http://localhost:8000` (or wherever the backend is actually reachable) — leaving it blank only breaks certificate generation specifically, nothing else.

## Local setup

Backend (`cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`) on `http://localhost:8000`, routes under `/api`. Frontend (`cd frontend && npm install && npm run dev`) on `http://localhost:5173`. Full instructions and the RLS acceptance check: see [README.md](../README.md#running-the-walking-skeleton).

## Database migration & reset

To set up a fresh project:
1. Run `db/schema.sql` in the Supabase SQL editor.
2. Create the `reports` Storage bucket — **private** (do not enable "Public bucket": nothing in this app relies on a public bucket URL, every download goes through the authenticated `POST /sessions/{id}/report` endpoint, and a public bucket would let anyone who knows or guesses a certificate's storage path read it directly, bypassing that endpoint's own authorization entirely). Storage bucket policies live in Supabase's own `storage` schema, not in `db/schema.sql` (this app's own `public` schema) — apply the following by hand, in the SQL editor, after creating the bucket (`fix/certificate-generation-wiring`; this policy has never been verified as applied on a real project before this task):
   ```sql
   create policy "reports bucket: authenticated upload"
   on storage.objects for insert
   to authenticated
   with check (bucket_id = 'reports');

   create policy "reports bucket: authenticated overwrite"
   on storage.objects for update
   to authenticated
   using (bucket_id = 'reports')
   with check (bucket_id = 'reports');
   ```
   No `select` (read) policy is needed today — the download endpoint always regenerates the PDF in memory and streams it back directly, it never reads the stored object back through the client SDK; add one only if a future feature needs to serve the already-stored file without regenerating it. The INSERT+UPDATE pair (not just INSERT) matches `upload_report_pdf`'s `upsert: "true"` (`app/repositories/storage.py`) — re-uploading for the same certificate number overwrites rather than erroring. Deliberately broad ("any authenticated user"): the API layer's own creator/approver/admin + `status == 'issued'` check (`app/routers/sessions.py`) is what actually authorizes the action — same defense-in-depth split as every other write in this app (`app/repositories/storage.py`'s own docstring).
3. Create the technician and approver demo accounts via Supabase Auth.
4. Run `db/seed.sql` to promote the approver account.

To reset: drop and recreate the project (or its schema), then re-run `db/schema.sql` and `db/seed.sql`.

For an already-provisioned (live) project that must not be reset, run the standalone additive migration files under `db/migrations/` instead — each brings that one live project up to date without touching existing data (ADR-0007's narrow exception to the "reset on every change" default): `002_registration_fields.sql` (the R 76-2 page-6 instrument fields), `003_pdf_certificate_and_verify.sql` (the `discrepancy_reports` table and the two `SECURITY DEFINER` functions this task adds — `set_report_storage_path`, `get_public_certificate_info`; see ADR-0009). Idempotent — re-running either is a no-op.

## Deploy (Vercel)

One project, one domain, two [Vercel Services](https://vercel.com/docs/services) defined in `/vercel.json` (repo root): `frontend` (Vite build, served at `/`) and `backend` (FastAPI, `backend/main.py` entrypoint shim, reachable under `/api`). Env vars are set in the Vercel dashboard, not committed anywhere — full list, and the post-deploy RLS acceptance check, are in [README.md](../README.md#deploying-to-vercel).

The project is pinned to region `bom1` (Mumbai) via a top-level `"regions": ["bom1"]` key in `vercel.json` (not nested inside `services.backend` — Vercel's schema rejects it there; a prior version had it there and it broke every deploy). This co-locates the `backend` function with the Supabase project's region (`ap-south-1`), avoiding a trans-Pacific round trip on every request. Not verified against Vercel's live schema (docs unreachable from this environment) — if deploys still fail schema validation on this key, remove `regions` from `vercel.json` entirely and set the region in the Vercel dashboard instead (Project Settings → Functions).

`services.backend.installCommand` (`cp -r ../engine ./engine && pip install -r requirements.txt`) copies the repo-root `engine/` package into the backend service's own bundle at build time — required because the `backend` service's `root` is `backend/`, which does not otherwise include its sibling `engine/` (ADR-0006). Nothing to configure by hand; this runs automatically as part of every deploy. `backend/engine/` is a generated, gitignored copy — never edit it directly.

## Common issues
