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

---

### [2026-09-26] — pin backend to bom1 region, fix README status

**Done:** Pinned the `backend` Vercel service to region `bom1` (Mumbai) in `vercel.json`, to co-locate the function with the Supabase project (`ap-south-1`) and avoid a trans-Pacific round trip per request. Fixed the stale `README.md` status line (was still "scaffolding") to reflect that the walking skeleton is deployed and Phase 0 (auth + per-user RLS round-trip) is verified in production. Added a one-line region note to `docs/runbook.md`'s Deploy section.

**Next:** Phase 1 engine spine.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — MPE lookup and change-point engine with boundary-value tests

**Done:** Built the pure-Python engine spine for Weighing: `engine/mpe.py` (R76-1 Table 6 lookup by class/load-band/verification-type, `in_service` doubling, band boundaries returned for traceability) and `engine/weighing.py` (`E = I + 1/2*e - deltaL - L`, `Ec = E - E0`, verdict `|Ec| <= mpe`, full derivation returned — never just pass/fail). Decimal arithmetic throughout, zero third-party imports. Wrote the canonical worked example as a failing test first, then implemented until green; then the actual acceptance criterion — a boundary-value table covering every Table 6 edge (all four classes, both sides), Max/Min, the inclusive verdict limit in both directions, and `in_service` doubling flipping a verdict. Added a mechanical purity check (AST-walks `engine/`, fails on any non-stdlib import — verified it actually catches a violation, not just passes trivially) and explicit no-silent-defaults tests (missing/wrong-typed inputs raise). Ran the full suite: **102 passed**. Filled `docs/architecture.md`'s Engine design section and `docs/testing.md`'s engine test strategy / boundary-value table / how-to-run.

**Next:** Phase 1's remaining item — the seven Pydantic model signatures (stubs) — then Phase 2, the Weighing vertical slice end to end.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — deterministic weighing load-sequence generator

**Done:** Added `engine/load_sequence.py` (`generate_load_sequence`): produces the applied-load (`L`) sequence for a Weighing test so the technician enters only I and ΔL, never L. Sourced anchors — Max; Min (only if ≥100mg per A.4.4.1, else omitted); every Table 6 band-transition load in range, read directly from `engine.mpe.BAND_TABLE` (no second copy of the band edges). ≥5 distinct loads (the 8.3.3 verification count — documented explicitly as *not* the ≥10 of full type evaluation). When anchors fall short of 5, fills evenly-spaced points strictly inside Band 1 — labeled `FILL_SPACING_STRATEGY` as a deterministic placeholder convention pending RRSL confirmation, never presented as sourced (`LoadEntry.kind`/`is_anchor` distinguishes them). Documented that bidirectional (up/down) expansion is deferred to the reading layer, and that multi-interval instruments are a known future extension. Extended `engine/types.py` with `LoadKind`/`LoadEntry`. Ran the full suite: **112 passed** (102 existing + 10 new, no regressions, purity test still green). Updated `docs/architecture.md`'s Engine design section.

**Next:** Phase 1's remaining item — the seven Pydantic model signatures (stubs) — then Phase 2, the Weighing vertical slice end to end.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — Pydantic contracts for Weighing reading and result

**Done:** Added `backend/app/contracts/` (`common.py`: `StrictDecimal` — string/int accepted, bare float rejected outright, serializes back to a JSON string; `Direction` enum; `weighing.py`: `WeighingReadingIn`, `WeighingResultOut`, and the two named adapter functions `reading_to_engine_kwargs`/`result_to_out`). `accuracy_class`/`verification_type` reuse `engine.types` enums directly (one source of truth, not a mirrored copy) — locked in by a test. Pinned `pydantic==2.10.3` in `backend/requirements.txt`. Checked pydantic's own default `Decimal` coercion empirically: it already converts a float via `str()` (not the naive lossy path), but the contract rejects float anyway per the task's explicit requirement, independent of that implementation detail. Ran the combined suite (`tests/` + `backend/tests/`): **137 passed** (112 existing + 25 new, no regressions, engine purity test still green — confirms Pydantic never leaked into `engine/`). Added a "Contracts / API validation layer" section to `docs/architecture.md`, including a flagged follow-up: `engine/` lives outside `backend/`'s own Vercel-service root, which the routes-wiring task will need to address.

**Next:** Wire these contracts into a real `POST /api/sessions/{id}/readings` route (Phase 2), which will need to resolve the `engine/`-outside-`backend/`-service-root deployment question noted above; then the remaining six test_type contracts, in the order set by Phase 3.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — fix: move regions to valid vercel.json location (schema validation)

**Done:** `vercel.json` was failing Vercel's schema validation on every deploy: `services.backend` should NOT have additional property `regions` (placed there in an earlier task). Moved `regions: ["bom1"]` out of `services.backend` to a top-level key instead. `vercel.com`/`openapi.vercel.sh` were still unreachable from this environment (egress-blocked), so this could not be verified against the live schema directly; the placement is reasoned from the schema error itself (only rejected *inside* the service object) plus corroborating evidence that Vercel's documented list of keys forced into a service when `services` is present (`functions`, `buildCommand`, `installCommand`, `devCommand`, `ignoreCommand`, `outputDirectory`, `framework`) does not include `regions`. Validated the resulting JSON is well-formed. Updated the region note in `README.md` and `docs/runbook.md` to reflect the corrected placement and spell out the dashboard fallback (Project Settings → Functions) if top-level `regions` is also rejected.

**Next:** Needs deploy-verification — push this branch's config to a preview and confirm schema validation now passes. If it still fails on `regions`, apply the fallback noted above (remove `regions` from `vercel.json`, set the region in the dashboard instead) rather than guessing at a third placement.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
