# Session Log

Purpose: an append-only log of working sessions on ScaleCert, so any session (cold or continuing) can quickly see what changed recently, what's next, and what's still open. Read the last 2–3 entries at the start of every session; append a new entry at the end of every session.

Append new entries at the bottom. Never edit or delete a past entry.

---

### [YYYY-MM-DD] — session summary template

**Done:** What was completed this session.

**Next:** What the following session should pick up.

**Open questions:** Anything unresolved that needs a decision or more information.

---

### [2026-09-26] — seed build plan, branch workflow, ADRs 0002/0003

**Done:** Seeded `docs/plan.md` with the full build plan (five principles, phases 0–4, lanes, open questions). Added the branch-per-task workflow rule to `CLAUDE.md`. Recorded ADR-0002 (new Supabase project) and ADR-0003 (hosting on Vercel with the Supavisor pooler).

**Next:** Schema migration.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — database schema, RLS, seed, and matching architecture docs

**Done:** Added `db/schema.sql` (full schema: seven tables, six enums, `get_my_role`/`handle_new_user` ported verbatim, certificate sequence, RLS policies on every table including the `42501` separation-of-duties tripwire) and `db/seed.sql` (demo approver promotion). Filled `docs/architecture.md`'s Database schema, Roles & permissions, Session lifecycle, and Out of scope sections; updated its STATUS line. Filled `docs/runbook.md`'s Environment variables and Database migration & reset sections. Recorded ADR-0004 (role promotion is seed-script-only) and ADR-0005 (schema as a single checked-in file; audit hash-chain deferred).

**Next:** Phase 0 — apply the schema to the new Supabase project, configure the pooler, seed the demo accounts.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — walking skeleton: health, whoami, and per-user RLS round-trip

**Done:** Added `backend/` (FastAPI: `/health`, `/whoami`, `/whoami/debug`, a per-request JWT-scoped Supabase client, no service-role client) and `frontend/` (minimal Vite + React app: login, three buttons calling the backend). Updated `README.md` with local run instructions and the RLS acceptance check (technician sees 1 visible profile row, approver sees more than 1).

**Next:** Make this deployable on Vercel as one domain.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — deploy walking skeleton to Vercel as one-domain services

**Done:** Confirmed the current (2026) Vercel approach via `vercel/examples/services/vite-fastapi` (the official template) rather than assuming prior knowledge: Vercel Services, `services.frontend` (`framework: "vite"`) + `services.backend` (`entrypoint: "main:app"`), with top-level `rewrites` routing by destination `{"service": ...}`. Added root `vercel.json` on that pattern; added `backend/main.py` as an entrypoint shim re-exporting the real app from `backend/app/main.py`; removed the old (pre-Services, now-superseded) `backend/vercel.json`. Moved the three existing routes under an `/api` prefix via `APIRouter(prefix="/api")` — handler bodies unchanged. Frontend now defaults to a same-origin relative `/api` base in production, overridable via `VITE_API_BASE` for local dev. CORS origin is now env-configurable (`CORS_ALLOW_ORIGIN`, default `http://localhost:5173`) instead of hardcoded, and is dev-only (same-origin `/api` needs no CORS in production). No service-role client added; `/api/whoami` still builds its client from the caller's JWT. Filled in `docs/architecture.md`'s API surface section (this is an API-surface change per the maintenance protocol). Updated `README.md` with a "Deploying to Vercel" section (env var list, one-domain routing, acceptance check).

**Next:** Apply `db/schema.sql` + `db/seed.sql` to the Supabase project (Phase 0 exit criteria), then actually deploy this branch's config to Vercel and run the acceptance check for real (technician sees 1, approver sees >1) — not yet done from this session, since it has no way to trigger a live Vercel deploy or sign in as the demo accounts.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
