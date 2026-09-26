# Architecture

Purpose: describe the system's structure — schema, engine, roles, API surface — as the single source of truth for how ScaleCert is built.

> STATUS: skeleton — to be populated in a later prompt. Do not treat as authoritative yet.

## System overview

## Scope (the 7 tests)

## Tech stack

## Database schema

## Engine design

## Roles & permissions

## Session lifecycle

## API surface

The FastAPI app is mounted entirely under `/api` (an `APIRouter(prefix="/api")` in `backend/app/main.py`), so route handler code and public URL match exactly — no prefix-stripping happens at the routing layer.

Deployed as two [Vercel Services](https://vercel.com/docs/services) in one project on one domain (`/vercel.json` at the repo root): `frontend` (the Vite build, `framework: "vite"`, served at `/`) and `backend` (the FastAPI app, `entrypoint: "main:app"` — a thin shim at `backend/main.py` re-exporting the real `app` from `backend/app/main.py`, following the entrypoint convention Vercel expects at the service root). A rewrite sends `/api/:path*` to the backend service; everything else falls back to the frontend service, which serves `index.html` (SPA fallback).

Locally, the same mount path is used: `uvicorn app.main:app` still serves `/api/health`, `/api/whoami`, `/api/whoami/debug` on `http://localhost:8000`. CORS is same-origin (and therefore off) in production; for local dev, an env-configurable allowed origin (`CORS_ALLOW_ORIGIN`, default `http://localhost:5173`) replaces what would otherwise be a permissive wildcard.

Current routes (walking-skeleton scope only — no business logic yet):
- `GET /api/health` — liveness, no auth, no DB.
- `GET /api/whoami` — per-request JWT-scoped read of the caller's own `profiles` row.
- `GET /api/whoami/debug` — same auth, returns the visible-row count; the RLS "who am I / what can I see" debug path from CLAUDE.md.

## PDF & audit

## Out of scope
