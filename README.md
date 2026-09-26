# ScaleCert

ScaleCert digitizes OIML R76 verification/certification for Non-Automatic Weighing Instruments (NAWIs) at India's RRSLs (Regional Reference Standards Laboratories), replacing paper-based verification workflows with a structured, auditable digital process.

## Stack

- **Engine + Backend:** Python / FastAPI, deployed on Vercel
- **Frontend:** React, deployed on Vercel
- **Data & Auth:** Supabase (Postgres, Auth, Row Level Security) + Supabase Storage for generated PDFs

## Where to go next

- [CLAUDE.md](./CLAUDE.md) — router, non-negotiable guardrails, and documentation maintenance protocol
- [/docs](./docs) — architecture, plan, testing strategy, and runbook

## Running the walking skeleton

This is the thin end-to-end round-trip (React → FastAPI → Supabase → back) with no business logic — it proves the pipe, nothing more.

### Backend

```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Runs on `http://localhost:8000`, with its three routes under `/api` (`/api/health`, `/api/whoami`, `/api/whoami/debug`) — the same mount path used in production. Needs these environment variables set (see `.env.example` at the repo root): `SUPABASE_URL`, `SUPABASE_ANON_KEY`. (`SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` are not used by this task.) Optionally set `CORS_ALLOW_ORIGIN` to change the allowed dev origin (defaults to `http://localhost:5173`).

### Frontend

```
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173`. Needs `frontend/.env` (see `frontend/.env.example`): `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_API_BASE=http://localhost:8000/api` for local dev (in production this is left blank and defaults to the same-origin relative path `/api`).

### How to verify

- `/api/health` returns ok.
- Logging in as `technician@scalecert.demo` → `/api/whoami` returns that profile with role `technician`; `/api/whoami/debug` shows visible profile count = 1.
- Logging in as `approver@scalecert.demo` → `/api/whoami/debug` shows visible profile count > 1.
- That technician-sees-1 / approver-sees-many difference is the proof RLS is applying per-user through a JWT-scoped client — not the service-role key.

## Deploying to Vercel

One Vercel project, one domain, two [Vercel Services](https://vercel.com/docs/services): `frontend` (the Vite build, served at `/`) and `backend` (the FastAPI app, reachable under `/api`). The routing is defined in `vercel.json` at the repo root — a rewrite sends `/api/:path*` to the backend service, and everything else (SPA fallback) to the frontend service, which serves `index.html`. There is no separate frontend deploy and backend deploy to keep in sync; it's one project, one domain, built and routed together.

The `backend` service is pinned to region `bom1` (Mumbai) in `vercel.json`, to co-locate it with the Supabase project (`ap-south-1`) and avoid a trans-Pacific round trip on every request from India-based users.

### Environment variables (set in the Vercel dashboard, per environment)

Backend (runtime — read by the FastAPI process on each request):
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` — not used by this task's routes; reserved for later privileged system tasks only (never for user-scoped reads).
- `SUPABASE_STORAGE_BUCKET`
- `DATABASE_URL` — noted for later direct-DB work; not used yet.

Frontend (build-time — baked into the static bundle by `vite build`, so these must be set before the build runs, not just at request time):
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

`VITE_API_BASE` is intentionally not set in production — leaving it unset keeps the frontend on the same-origin relative `/api` default.

### Acceptance check

After deploy, visit the site and log in as the technician, then as the approver:
- `/api/whoami/debug` returns `visible_profile_count: 1` for `technician@scalecert.demo`.
- `/api/whoami/debug` returns `visible_profile_count` greater than 1 for `approver@scalecert.demo`.
- That split is the proof RLS is applying per-user in production, through a JWT-scoped client — not the service-role key.

## Status: walking skeleton deployed; Phase 0 (auth + per-user RLS round-trip) verified in production
