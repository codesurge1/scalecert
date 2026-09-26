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

Runs on `http://localhost:8000`. Needs these environment variables set (see `.env.example` at the repo root): `SUPABASE_URL`, `SUPABASE_ANON_KEY`. (`SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` are not used by this task.)

### Frontend

```
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173`. Needs `frontend/.env` (see `frontend/.env.example`): `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE` (defaults to `http://localhost:8000`).

### How to verify

- `/health` returns ok.
- Logging in as `technician@scalecert.demo` → `/whoami` returns that profile with role `technician`; `/whoami/debug` shows visible profile count = 1.
- Logging in as `approver@scalecert.demo` → `/whoami/debug` shows visible profile count > 1.
- That technician-sees-1 / approver-sees-many difference is the proof RLS is applying per-user through a JWT-scoped client — not the service-role key.

## Status: scaffolding
