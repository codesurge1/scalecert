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

### [2026-09-26] — Weighing API: instruments, sessions, load sequence, readings

**Done:** Added the minimum backend chain for the Weighing vertical slice, all under `/api`, all through a new reusable `app.deps.get_auth_context` dependency (per-request JWT-scoped client + resolved `auth.uid()` via GoTrue, no service-role client). `POST/GET /api/instruments[/{id}]`; `POST /api/sessions`, `GET /api/sessions/{id}` (creates the session's `weighing` `session_test_selection` row too); `GET /api/sessions/{id}/weighing/sequence` (calls `engine.load_sequence.generate_load_sequence` — server-derived, never stored); `POST /api/sessions/{id}/weighing/readings` (regenerates the sequence, looks up `L` for the submitted `sequence_no`, calls the engine, writes `test_readings` + `test_results` together — insert-then-insert with a rollback-delete on result-insert failure, since supabase-py has no client-side multi-table transaction — then a non-fatal `audit_log` insert). Split `backend/app/` into `contracts/` (added `instrument.py`, `session.py`; extended `weighing.py` with the narrower client-facing `WeighingReadingSubmitIn`/`WeighingSequenceEntryOut`; extended `common.py` with `IndicationType`/`SessionStatus`/`TestType`), `services/` (pure: `weighing.py` — sequence_no→L lookup + engine orchestration; `sessions.py` — the not-draft rule), and `repositories/` (thin, mockable DB IO) — specifically so the pure logic is unit-testable without live Supabase (this sandbox has no egress to one). Found and fixed a real bug during testing: PostgREST returns `numeric` columns as JSON floats, which would have tripped `StrictDecimal`'s client-input float rejection on every normal read — `app.db_decimal.decimal_from_db_value` (a deliberately different, DB-row-safe policy) now converts before those values ever reach an `Out` contract. Ran the combined suite: **179 passed** (137 existing + 42 new, no regressions, engine purity test still green). Updated `docs/architecture.md`'s API surface section in full. Also added a throwaway `frontend/public/apitest.html` manual-test harness (separate branch, `test/api-harness`) for clicking through this same API chain on the preview deploy.

**Next:** Verify the DB-integration path on the preview deploy (see the checklist in that PR description); then the frontend forms for this slice (Phase 2), and after that, submit → approve-by-a-different-user → PDF → public verify to close out the vertical slice.

---

### [2026-09-26] — fix: move regions to valid vercel.json location (schema validation)

**Done:** `vercel.json` was failing Vercel's schema validation on every deploy: `services.backend` should NOT have additional property `regions` (placed there in an earlier task). Moved `regions: ["bom1"]` out of `services.backend` to a top-level key instead. `vercel.com`/`openapi.vercel.sh` were still unreachable from this environment (egress-blocked), so this could not be verified against the live schema directly; the placement is reasoned from the schema error itself (only rejected *inside* the service object) plus corroborating evidence that Vercel's documented list of keys forced into a service when `services` is present (`functions`, `buildCommand`, `installCommand`, `devCommand`, `ignoreCommand`, `outputDirectory`, `framework`) does not include `regions`. Validated the resulting JSON is well-formed. Updated the region note in `README.md` and `docs/runbook.md` to reflect the corrected placement and spell out the dashboard fallback (Project Settings → Functions) if top-level `regions` is also rejected.

**Next:** Needs deploy-verification — push this branch's config to a preview and confirm schema validation now passes. If it still fails on `regions`, apply the fallback noted above (remove `regions` from `vercel.json`, set the region in the dashboard instead) rather than guessing at a third placement.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — frontend foundation: Tailwind, shadcn, app shell, auth, instrument registration

**Done:** Replaced the throwaway login skeleton with the real frontend foundation. Tailwind CSS v4 (`@tailwindcss/vite`, CSS-first, no `tailwind.config.js`) + shadcn/ui — `ui.shadcn.com` is egress-blocked from this sandbox (same as `vercel.com`), so the CLI couldn't run; wrote `components/ui/{button,input,label,select,card,form,table,dialog,sonner,badge,skeleton}.jsx` by hand to shadcn's own standard shape, and committed `components.json` so a future CLI run in an environment with network access still targets the same structure. Institutional design tokens as CSS variables (`src/index.css`): restrained deep slate-blue primary, cool slate neutrals, small radius, semantic success/warning/destructive kept separate from primary. `react-router-dom` with an `AuthGate` layout route (loading skeleton while the session check is in flight, never a redirect flash) and an `AppShell` layout (top bar: wordmark, nav, email + role badge via the existing `/api/whoami`, logout). Real Supabase auth (`src/lib/supabase.js`) and a central `apiFetch` helper (`src/lib/api.js`) that attaches `Authorization: Bearer` automatically. Built the one real screen: `/instruments` (list, with loading/empty/error states) and `/instruments/new` (shadcn Form + react-hook-form, `POST /api/instruments`) — numeric fields (`e_value`/`d_value`/`max_capacity`/`min_capacity`) stay strings from the input to the fetch body, never `Number()`/`parseFloat()`, matching the backend's `StrictDecimal` rejection of bare floats; a comment at the call site says why. `npm run build` succeeds (verified, see reply). Did not touch `apitest.html`, the backend, the engine, or `vercel.json`. Updated `docs/architecture.md` with a Frontend section.

**Next:** Verify on the preview deploy (log in, see the shell, register an instrument, see it in the list — full checklist in the reply/PR description); then the session/reading/verify/approve screens, and a separate cleanup task to remove `apitest.html` once they exist.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — weighing session UI with live derivation display

**Done:** Built the core technician workflow on top of the existing design system: `StartVerificationDialog` (pick `verification_type`, `POST /api/sessions`, route to the new session) triggered from a "Start verification" action added to `/instruments`; `/sessions/:id` loads the session, its instrument, and the generated load sequence in parallel and renders a header (instrument, verification type, status badge, selected tests), `LoadSequenceTable` (per-load `sequence_no`/`L`/`m`/`mpe`, with a `KindBadge` that visually distinguishes sourced anchors from `fill` placeholder points — tooltip + caption owning the open item rather than flattening it away — and independent ↑/↓ status per load), and `ReadingEntryPanel` (I and ΔL visually grouped as the only technician-entered values, `L` shown read-only from the sequence, direction toggle, E0 field defaulted to "0" with a flagged note that zero-capture isn't a dedicated step yet, and on submit the full derivation — L, I, ΔL, E0, E, Ec, mpe, margin — rendered under a prominent PASS/FAIL badge). A 409 (session not draft) renders as a specific message and disables submission. Numeric fields stay strings from input to POST body, same convention as the Instrument Registration form. Deleted `frontend/public/apitest.html` — superseded by this real UI. Noted a real gap rather than working around it: there's no `GET .../weighing/readings` list route yet, so the readings table is local-state-only and refresh-fragile (the sequence and the API's own state are unaffected). `npm run build` succeeds (see reply). Did not touch backend/engine/vercel.json; no submit-for-review/approve/PDF/verify screens — sessions stay `draft`. Updated `docs/architecture.md`'s Frontend section.

**Next:** Verify on the preview deploy (start a session → see the sequence → enter readings both directions on a couple of loads → see PASS/FAIL derivations — checklist in the reply/PR description); then submit-for-review/approve/return, PDF generation, and the public verify page.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — fix: package engine module into the deployed backend function

**Done:** Confirmed production bug: the deployed `backend` Vercel Service crashed at import time (`ModuleNotFoundError: No module named 'engine'`) on every authed route, because Vercel builds that service from `backend/` as its root and the sibling repo-root `engine/` package isn't included by default. `vercel.com` docs were still egress-blocked (tried again first); reasoned from Vercel's Python packaging model and real GitHub examples (`vercel/vercel` PR #5030, a `vercel/vercel-plugin` migration-docs PR) instead — neither source could confirm whether `includeFiles` can reach outside a service's own `root` under the newer `services` shape, so rather than gamble on an unconfirmed, potentially-silent-failure mechanism, chose a build-time copy: `services.backend.installCommand = "cp -r ../engine ./engine && pip install -r requirements.txt"` (fails loudly if the sibling-directory assumption is wrong, unlike a silently-empty glob). `backend/engine/` gitignored — generated, never a second source of truth. Locally reproduced the exact reported error in an isolated temp copy of `backend/` with no `engine/` present, then confirmed the same copy step resolves it — going further, booted the real `app.main:app` FastAPI app (fresh venv, real `requirements.txt`) from within that simulated function root and listed its actual routes. What could NOT be verified locally: whether Vercel's real build actually has the sibling `engine/` present when `installCommand` runs — that's the one thing only the next real deploy proves. Re-ran the full suite from repo root: **179 passed**, unchanged (pure deploy-config fix, no code touched). Recorded ADR-0006. Updated `docs/architecture.md` (resolved the flagged known-follow-up) and `docs/runbook.md`'s Deploy section.

**Next:** Verify on the actual next deploy that authed routes no longer 500 (`/api/instruments`, `/api/sessions/...` with a valid token). If the `installCommand` assumption turns out wrong (build fails on the `cp` step), fall back to making `engine/` a pip-installable local package (ADR-0006 option 2) rather than gambling further on `includeFiles`.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — Weighing entry rebuilt as an OIML R 76-2 form table (bidirectional)

**Done:** Replaced the card-per-reading `LoadSequenceTable`/`ReadingEntryPanel` pair with `WeighingFormTable` — a single table faithful to the OIML R 76-2 "1 Weighing performance" form's own layout (page 10 of the standard, extracted for reference via a temp `pypdf` venv since `pdftoppm`/poppler-utils and the system Python's pip were both broken/absent): header block (Application no./Type designation read-only, Date/Observer editable, e and "resolution during test" = `COALESCE(d_value, e_value)`, an environmental-conditions table, the zero-device-status and initial-zero-setting radio rows, and the formula line `E = I + ½e − ΔL − L` / `Ec = E − E0` printed verbatim), a main data table (one row per generated load, `L`/`mpe` read-only, paired ↓/↑ column groups for editable I/ΔL and computed E/Ec, a per-row PASS/FAIL/Pending badge), a single `E0` field, and an overall "Check if |Ec| ≤ |mpe|" PASSED/FAILED/INCOMPLETE box. Framed explicitly as a faithful reproduction of the FORMAT for data entry, not a copy of the copyrighted OIML document. Implemented the direction mapping exactly as specified — the form's "↓" is the increasing-load pass (API `direction: "up"`), "↑" is the decreasing-load pass (API `direction: "down"`) — documented in-code at `FORM_COLUMNS`. Editing a direction's I/ΔL submits `POST .../weighing/readings` on ΔL-blur or Enter. Two pre-existing gaps carried forward and flagged, not solved (both require backend work out of scope here): no `PATCH` for `test_sessions`/`session_test_selection`, so all header-block fields are local-only state, noted in the UI; no `GET .../weighing/readings` list route, so filled table cells are refresh-fragile, noted via a read-only banner on non-draft sessions. Numeric fields stay strings from input to POST body throughout, same convention as the rest of the frontend. `npm run build` succeeds. Did not touch backend/engine/vercel.json; no PDF, submit-for-review/approve, or public verify screens. Updated `docs/architecture.md`'s Frontend section and STATUS line.

**Next:** Verify on the preview deploy (checklist in the branch reply); then submit-for-review/approve/return, PDF generation (which will reuse this exact form layout), and the public verify page. Adding the session/selection-update endpoint and the readings-list endpoint would close both flagged gaps.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — Weighing screen: visual fidelity pass against the real R 76-2 page-10 form

**Done:** The prior form-table pass had the right fields but read as an app-styled table, not the official form. Installed `poppler-utils` into this sandbox (unavailable in the earlier task, worked around then via `pypdf` text extraction) and read the OIML R 76-2 PDF's page 10 as a rendered image — the actual source, not a text reconstruction — then rebuilt `WeighingFormTable.jsx` to match it precisely: a bordered white "sheet" (serif font, black rules, no rounded corners, centered, outside the app's shadcn styling but still inside the app shell/nav) reproducing the masthead ("OIML R 76-2: 2007 (E)" / "Report page …./…."), the bold title and "(Calculation of the error)" subtitle, a two-column header block (dotted fill-in lines for Application no./Type designation/Date/Observer/e/resolution, plus the environmental grid — corrected to the form's real orientation: rows Temp./Rel.h./Time/Bar.pres., columns At start/At max/At end, since the prior pass had this transposed), the zero-device and initial-zero-setting lines as ☐-style square checkboxes, the formula block printed verbatim with the E0 footnote asterisk, and the main table rebuilt to the form's actual 10-column, quantity-major order (Indication↓↑, Add.load↓↑, Error↓↑, Corrected error↓↑, then a single un-split mpe column) — the prior pass had grouped columns by direction instead of by quantity, which worked but didn't match the source, and had an extra "Result" badge column not present on the real form (dropped; pass/fail is now conveyed via the colored Ec cells, same as the form implies). Direction mapping (↓=increasing/API "up", ↑=decreasing/API "down") is unchanged and still documented in-code at `FORM_COLUMNS`. All prior functionality preserved exactly: submit-on-ΔL-blur-or-Enter, live E/Ec fill-in with pass/fail coloring, the overall PASSED/FAILED/INCOMPLETE check (now read-only Passed/Failed boxes matching the form, with an INCOMPLETE caption alongside since the paper form has no such state), Remarks, decimal-as-string discipline throughout, and the two previously-flagged gaps (no session-update endpoint, no readings-list endpoint) — both still noted in a caption below the sheet rather than inside it, so the sheet itself stays a clean reproduction. `npm run build` succeeds. Did not touch backend/engine/vercel.json, `SessionPage.jsx`, or any other screen. Updated `docs/architecture.md`'s Frontend section.

**Next:** Verify on the preview deploy (checklist in the branch reply) — in particular that the quantity-major column reordering didn't regress which cell a given ↓/↑ input actually submits to. Then submit-for-review/approve/return, PDF generation (can now reuse this exact visual layout directly), and the public verify page.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — raise the Weighing verification load-sequence target to 10 (lab convention)

**Done:** Changed `engine.load_sequence.MIN_VERIFICATION_LOAD_COUNT` from 5 to 10. Rewrote the surrounding module docstring and inline comment to state the distinction honestly and explicitly, per the task: OIML clause 8.3.3's sourced minimum is ≥5 distinct test loads and that figure does not change; this project's own working target is now 10, a lab convention chosen because spreading more load points across the range gives a more thorough verification and matches common RRSL practice — it is NOT an OIML requirement of 10, and it is a coincidence of numbering (not the same figure) that a *different* "≥10" already existed elsewhere for full type evaluation, a separate out-of-scope test battery. Sourced anchors (Max; Min when ≥100mg; in-range band transitions) are untouched — same logic, same tagging; only the fill-count shortfall calculation changes, automatically, since it derives from the constant. Fills remain evenly spaced inside Band 1, deterministic, tagged `FILL`, never colliding with an anchor's exact load. Updated `tests/test_load_sequence.py`: the "four anchors" test's fill-count assertion and comment now reflect the shortfall against 10 (was hardcoded to the old shortfall of 1, now derives as `MIN_VERIFICATION_LOAD_COUNT - 4` = 6); added `test_typical_class_iii_instrument_reaches_target_of_ten` for the task's specified instrument (Class III, e=10, Max=30000, Min=200 → 4 anchors, 6 fills, 10 total, distinct, deterministic). The other existing tests needed no changes — they already asserted against the `MIN_VERIFICATION_LOAD_COUNT` constant rather than a hardcoded number, so they adapted automatically. Full suite: **180 passed** (engine + backend, incl. `tests/test_purity.py` still green — no new imports, stdlib-only, Decimal-only, unchanged). Updated `docs/architecture.md`'s Engine section (same careful two-numbers framing) and corrected a now-stale `docs/plan.md` Phase-1 bullet that still said "Load count is 5, not 10" (code-wins rule — left unfixed it would actively contradict the code). Did not touch `backend/`, `frontend/`, or `vercel.json` — pure engine + docs change.

**Next:** Verify on the preview deploy that `GET .../weighing/sequence` now returns 10 loads for a typical instrument and the Weighing form table renders all of them correctly (it already handles an arbitrary row count, so no frontend change should be needed — worth confirming). If RRSL ever confirms an actual fill-spacing convention, `FILL_SPACING_STRATEGY` is still the one place to change it.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms) — now filling more points (up to 9) inside Band 1 when the whole range sits there; same open item, larger in practice.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — instrument→session→test navigation with a session overview

**Done:** Added the missing navigation layer: Instruments list → Instrument detail (its sessions) → Session overview (the 7-item checklist with statuses) → a test page. The verification-type choice now happens exactly once, at session creation, never when opening a test — removed the old flat path where clicking an instrument's "Start verification" immediately asked initial/subsequent and landed straight in the Weighing table.

Backend (two new read-only GETs, schema/engine/readings-submission logic untouched):
- `GET /api/sessions/{id}/weighing/readings` — every submitted Weighing reading paired with its computed result (`WeighingReadingRecordOut` in `app/contracts/weighing.py`, built by `reading_and_result_to_record_out` from the stored `test_readings.data`/`test_results.result` — never recomputed). Dedupes to the latest reading per `(sequence_no, direction)` by `created_at`, since there's no update endpoint and a resubmission is a second insert. New repo functions `readings_repo.list_readings`/`list_results`. RLS already allowed creator+approver/admin to select both tables — no new policy needed.
- `GET /api/instruments/{id}/sessions` — an instrument's sessions, newest first, reusing `SessionOut`/`session_out_from_rows` rather than a slimmer duplicate contract. New repo function `sessions_repo.list_sessions_for_instrument`.
- 6 new router tests (paired records, dedup-to-latest, orphan-reading defensiveness, 404s for both routes, sessions-list ordering) — full suite **186 passed** (was 180), purity still green, no schema/engine change.

Frontend:
- `InstrumentDetailPage.jsx` (new, `/instruments/:id`) — instrument header + its sessions list (`GET .../sessions`), "Start verification" (existing `StartVerificationDialog`, now triggered here instead of from the instruments list) creates a session and routes to its overview.
- `InstrumentsListPage.jsx` — each row's action is now a "View" link to the instrument detail page, not an inline `StartVerificationDialog` trigger.
- `SessionPage.jsx` (`/sessions/:id`) — rebuilt as the session overview: summary header card + the OIML clause 8.3.3 seven-item checklist (`TEST_ROWS`), each row's applicability computed client-side from the instrument (Discrimination N/A for digital, Tilting mobile-only, Sensitivity non-self-indicating-only — no `session_test_selection` rows exist yet for the five non-Weighing test_types, so this can't be server-derived until the Phase-3 test selector exists). Weighing's status (Not started/In progress/Complete+verdict) is derived from sequence-length×2 vs. readings-GET's count; the other five show "Coming soon"; `zero_tare` (no own `test_type` in the schema — tracked as a Weighing variant) is listed for completeness but never itself startable.
- `WeighingSessionPage.jsx` (new, `/sessions/:id/weighing`) — the actual Weighing form, reached only from the overview's Start/Open button. Fetches session+instrument+sequence+readings in parallel and renders `WeighingFormTable` with the new `initialReadings` prop.
- `WeighingFormTable.jsx` — added `initialReadings`; `cellsFromInitialReadings()` seeds the cells state (and `E0`) from it via a lazy `useState` initializer, so a page load/refresh reconstructs exactly what was already submitted — closes the "refresh loses progress" gap flagged in the previous task.
- `App.jsx` — added `/instruments/:id` and `/sessions/:id/weighing` routes.
- `npm run build` succeeds.

Did not touch `engine/`, `db/schema.sql`, the readings-submission route/service, or any RLS policy. Did not build the other 6 test forms, the PDF, submit/approve, or the verify page. Updated `docs/architecture.md` (API surface: the two new GETs; Frontend: the full navigation rewrite, the pre-fill mechanism, and the closed readings-list gap) and its STATUS line.

**Next:** Verify on the preview deploy (checklist in the branch reply). Then: the per-session test selector (Phase 3) to give the other five test_types real `session_test_selection` rows and eventually their own forms; the session/selection update endpoint for the still-local-only header-block fields; submit-for-review/approve/return; PDF; verify page.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — fix: harden session DB errors and rebuild add-test flow

**Part A — fixed a real production 500.** `POST /api/sessions` was 500ing after a table wipe. A prior read-only diagnosis (code-only, no live DB access) had narrowed it to `repositories/sessions.py`'s `insert_session`/`insert_session_test_selection` doing `rows = ....execute().data; return rows[0]` with no guard — a bare `IndexError` on an empty PostgREST response, and no `try/except` around the call at all, so an outright `postgrest.exceptions.APIError` (RLS rejection, malformed id, ...) was equally unhandled. Fixed systemically: new `app/repositories/errors.py` (`RepositoryError`, `run_select`, `run_insert`) that every insert/select helper in `repositories/{instruments,sessions,readings}.py` now goes through instead of a bare `.execute().data` — `run_select` treats an empty result as the normal SELECT outcome it is, only wrapping an outright `APIError`; `run_insert` wraps `APIError` *and* guards the empty-`rows` case. A "resolve a path-param id" `RepositoryError` (`_get_instrument_or_404`/`_get_session_or_404` in both routers) folds into the existing 404 (a malformed id belongs in the same "can't resolve to anything" bucket already documented for not-found/not-visible), with the underlying PostgREST error kept in `detail` for diagnosability. A write-path `RepositoryError` (`create_session`'s two-step insert, `submit_weighing_reading`'s reading/result inserts, `create_instrument`) maps `likely_rls` to 403, anything else to 500, again with a specific `detail`. `app/main.py` registers a global `@app.exception_handler(RepositoryError)` as the backstop for every route without a local catch — a `RepositoryError` can no longer reach FastAPI's default handling and come back as an opaque, detail-free 500. `SessionIn.instrument_id` is now `pydantic.UUID4` (was a bare `str`) — the frontend-bug shape (empty/`"undefined"`/garbage) now 422s at the contract layer before any DB call. Test coverage: `backend/tests/repositories/test_errors.py` (new — pure unit tests proving both failure shapes never escape as `IndexError`/`APIError`), and — notably — `POST /sessions` had **zero router-level tests** before this task despite being the endpoint that was 500ing; added happy-path, instrument-not-found, malformed-id-422, and `RepositoryError`-mapping cases to `test_sessions_router.py`, plus equivalent malformed-id/mapping cases to `test_instruments_router.py`.

**Part B — rebuilt the flow to "Add test → pick from the 7 → that test's table opens."** New `src/lib/testChecklist.js` (the shared `TEST_ROWS`, moved out of `SessionPage.jsx` so it can't drift from the picker) and `src/components/session/AddTestDialog.jsx` — a dialog listing the OIML 8.3.3 checklist, every row disabled/greyed except Weighing (conditional N/A reasons shown for Discrimination/Tilting/Sensitivity, "Coming soon" for the rest), picking Weighing routes to `/sessions/:id/weighing`. `SessionPage` (the overview) no longer renders all 7 checklist items as permanent rows — that full picker view moved into the dialog — and instead shows a "Tests added to this session" table that, today, always lists Weighing directly (its `session_test_selection` row is created unconditionally at session creation, so it's never genuinely "not added"), with live status and a Start/Open button, plus the "Add test" button that opens the picker. `StartVerificationDialog` renamed "Start verification" → "New verification session" throughout (button, dialog title, submit button, toast, `InstrumentDetailPage`'s empty-state copy) specifically to stop "session" and "test" reading as the same action now that a session can hold several tests. Verified the overview/Weighing pages still degrade to clean empty states (no crash) on a fully wiped DB, now backed by Part A's fix rather than accidentally.

`npm run build` succeeds. Full suite: **209 passed** (was 186 — 9 new `repositories/test_errors.py` unit tests, +5 net in `test_session_contract.py` (one new parametrized malformed-id test), +7 in `test_sessions_router.py`, +2 in `test_instruments_router.py`). Did not touch `engine/`, `db/schema.sql` (RLS policies unchanged — this task handles their rejections gracefully, doesn't alter them), or the other 6 test forms/PDF/approve/verify. Updated `docs/architecture.md` (API surface: the hardening mechanism and UUID4 validation; Frontend: the Add-test flow and the renamed session-creation dialog) and its STATUS line.

**Next:** Verify on the preview deploy (checklist in the branch reply) — in particular that `POST /api/sessions` actually returns 201 against the real, now-empty-then-repopulated tables, which is the one thing this sandbox's mocked-DB tests can't prove. Then: the per-session test selector (Phase 3, would let the "Tests added" list reflect real selections for the other five test_types instead of only ever showing Weighing); the session/selection update endpoint; submit-for-review/approve/return; PDF; verify page.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-26] — derive and validate accuracy class from e/Max/Min

**Done — Part A (engine).** New `engine/classification.py` (`classify_instrument`, pure — stdlib + Decimal only, purity test still green) implements OIML R76-1 Table 3: given `e`/`Max`/`Min` (and optional `d`), computes `n = Max/e` and evaluates all six Table 3 rows (Classes II and III each split into a lower-`e` and higher-`e` row with different `n_min`/Min requirements — the real shape of Table 3, not a simplification). Each row's `n_max` is read directly off `engine.mpe.BAND_TABLE`'s last band edge for that class rather than duplicated as a second hardcoded number (Table 6 only needs bands up to where a class stops applying, so the two are the same figure by construction — reused, per the task's own instruction not to duplicate silently). Returns `ClassificationResult` (new in `engine/types.py`): `n`, `qualified_classes` (zero/one/more, most-precise-first), `reason` (populated only when empty, naming exactly which class(es) were in `e`-range and which constraint — `n` too high/low, or Min too low — failed for each). `e` must be 1/2/5 × 10^k grams (clause 3.4.2), checked via `Decimal.normalize()`'s digit tuple — no float/log math, no rounding risk. `d`, if given, is checked against `d < e ≤ 10d`. `min_capacity` is required here (a deliberate difference from `load_sequence`'s optional Min, which is optional for an unrelated reason). Type/domain errors still raise `TypeError`/`ValueError` immediately, matching the rest of the engine; a "doesn't fit any class" outcome is a returned result, not an exception, since the API layer needs to turn it into a 422 body, not catch an exception.

**Done — Part B (engine tests).** `tests/test_classification.py`, 43 tests, all real: one valid case per class, `n`-at-exact-boundary cases (both ends, multiple classes), Min-too-low cases, a genuinely multi-class-qualifying case (`e=1g, Max=8000g, Min=50g` → both II and III), `e`-format validation (valid and invalid, parametrized), the `d`/`e` relationship, and type/domain errors. The actual bug scenario got three dedicated tests, reasoned through carefully rather than guessed: the old free-choice model let a client force `accuracy_class="III"` with `e=1g, Max=15000g` (`n=15000`, exceeding Class III's own `n_max=10000`) — under the new model that combination can *never* qualify for Class III; with adequate Min it correctly resolves to Class II instead (`n=15000` fits Class II's high-`e` row, `[5000,100000]`); with inadequate Min (too low for every class the `e`/`n` combination could otherwise fit) it's cleanly rejected with a reason naming the specific failures, never silently stored as an invalid class.

**Done — Part C (backend).** `InstrumentIn.accuracy_class` is now `Optional[AccuracyClass] = None` — only used to disambiguate when multiple classes qualify, otherwise ignored entirely; `min_capacity` changed from optional to required (classification needs it). New `app/services/instruments.py` (`derive_accuracy_class`, pure, unit-tested directly in `test_instruments_service.py` — no DB/HTTP) is the one place `classify_instrument` is called from the API layer: exactly one qualifying class → that class, regardless of any client hint; zero → raises `InstrumentNotClassifiable`; more than one with no valid client hint → raises `AmbiguousAccuracyClass`. `routers/instruments.py`'s `create_instrument` maps both to a 422 with the engine's own reason, before anything is written — `instrument_insert_payload`/`insert_instrument` now take the server-derived class as an explicit argument (never `payload.accuracy_class` directly), so what's stored can never be the client's own unchecked value even by accident. RLS/auth/the hardened repository-error handling (previous task) are untouched. Updated the pre-existing `test_instrument_contract.py`/`test_instruments_router.py` fixtures that predated this change (several used `e=1, Max=5000, Min=10, accuracy_class=III`, which — now that it's actually checked — isn't Table-3-valid: Min=10 < the 20g Class III requires; harmless before this task since accuracy_class was a trusted free field, a real bug afterward) and added dedicated new tests for: registering without `accuracy_class` at all, rejecting `e`/Max/Min that fit no class, requiring disambiguation when multiple qualify, accepting a valid disambiguation, and rejecting one that isn't among the qualifying set.

**Done — Part D (frontend).** `InstrumentRegisterPage.jsx`'s free-choice accuracy-class `<Select>` is gone. `src/lib/accuracyClass.js` mirrors `engine/classification.py` client-side (same six Table 3 rows, same rules) using string/BigInt decimal arithmetic throughout — never `Number()`/`parseFloat()`, verified against the Python engine's actual output for nine cases (including the bug scenario) via a throwaway node script before being wired in. As the technician fills `e`/Max/Min (Min now required, no longer marked optional), a live preview shows: exactly one class → a read-only `Badge` ("Class III — derived from e, Max, n=6000"), submit sends no `accuracy_class` at all; zero classes → the engine's rejection reason inline in red, submit disabled; more than one → a `<Select>` populated only with the qualifying classes, submit disabled until chosen. The server re-derives independently on the real `POST` regardless of what the preview showed — the mirror is documented as instant-feedback-only, never the actual source of truth. `npm run build` succeeds.

Full suite: **265 passed** (engine 156 incl. the 43 new classification tests, backend 109 incl. new service/router/contract tests), purity still green. Did not touch `engine/load_sequence.py`, `engine/weighing.py`, `WeighingFormTable.jsx`, RLS policies, or any other test form. Updated `docs/architecture.md` (Engine: the new classification section, placed before MPE lookup since it now runs first; API surface: the instruments-POST bullet; Frontend: the Instrument Registration rewrite) and its STATUS line.

**Next:** Verify on the preview deploy (checklist in the branch reply) — in particular that a real registration attempt with genuinely out-of-spec numbers (like the original `n=15000` bug case) now 422s cleanly instead of ever reaching the DB. Then: the per-session test selector (Phase 3); the session/selection update endpoint; submit-for-review/approve/return; PDF; verify page.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification (per-sub-range e/n/Min) is a known future extension — not handled by `classify_instrument`, same limitation as `load_sequence`.

---

### [2026-09-26] — feat: instrument registration as OIML R 76-2 page-6 form

**Done — Part A (schema).** Page 6 of R 76-2 ("General information concerning the type") was read as a rendered image (`pdftoppm`, same PDF used for the Weighing-form fidelity task) — successfully, full layout captured. Added 21 nullable columns to `instruments` in `db/schema.sql`: `applicant`, `instrument_category`, power supply (`u_nom`/`u_min`/`u_max`/`mains_frequency`/`battery_u_nom`), `printer_status`, `zero_device_type`, `tare_device_type`, `initial_zero_setting_range_pct`, `temperature_range_min`/`temperature_range_max`, load cell (`load_cell_manufacturer`/`load_cell_type`/`load_cell_capacity`/`load_cell_number`/`load_cell_class_symbol`), `software_version`, `identification_no`, `interfaces`. Since a live/demo project may already have real instruments in it, forcing ADR-0005's usual "drop and re-apply the whole schema" for a purely additive, nullable-only change was disproportionate — wrote **ADR-0007** as a narrow, explicit exception (additive/idempotent/nullable-only only, `schema.sql` stays authoritative for a fresh apply, this does not authorize a general migration workflow) and added `db/migrations/002_registration_fields.sql`, a standalone idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` script the operator runs by hand against the live project — see the branch reply for the exact statements.

**Done — Part B (backend).** Extended `InstrumentIn`/`InstrumentOut` with all 21 fields (optional, numeric ones as `StrictDecimal`), plus `Literal[...]` types for `printer_status`/`zero_device_type`/`tare_device_type` — actually enforced at the contract layer (unlike `session_test_selection.zero_device_status`'s existing, unenforced comment-only precedent). Accuracy-class derivation (`app/services/instruments.py`, `engine/classification.py`) is completely untouched — still server-derived, never client-chosen. 9 new contract tests + 1 new router test (page-6 fields round-trip through insert/output, including the float→Decimal PostgREST conversion and pre-migration rows missing the new keys entirely).

**Done — Part C (frontend).** Rebuilt `InstrumentRegisterPage.jsx` from scratch as the page-6 form: a bordered serif document sheet (matching `WeighingFormTable`'s established visual style), reproducing the form's actual layout top to bottom (identity block, Complete-instrument/Module line, four accuracy-class ovals now auto-ticked from the derivation instead of a `Badge`, self-/semi-/non-self-indicating tick-boxes mapped onto the existing `indication_type` enum, Min/e/Max/d/n plus three blank multi-interval rows, T=+/− temperature, the five-field power-supply line, zero-setting/tare-device tick-box columns with "Combined zero/tare device" folded into `tare_device_type`, initial-zero-setting-range + a read-only temperature-range summary, printer tick-boxes, and the identification/software/interfaces/load-cell block). Fields with no backing column (module/error-fraction testing, e1/Max1/d1/n1 sub-rows, "Instrument submitted"/"Connected equipment"/evaluation period/date of report/observer/remarks) render as inert blank form elements for layout fidelity, never misleadingly-interactive disabled inputs. Extracted `FormLine`/`FormCheckbox` out of `WeighingFormTable.jsx` (private before this task) into shared `src/components/oiml/FormPrimitives.jsx`, plus a new third primitive `FormBox` for boxed numeric fields — both OIML-form screens now stay pixel-identical by construction. The derived-class JS mirror (`src/lib/accuracyClass.js`) is unchanged and still the instant-feedback layer only; the server re-derives independently on every submit.

`npm run build` succeeds (720.48 kB bundle, no new warnings beyond the pre-existing chunk-size notice). Full suite: **275 passed** (was 265 — 9 new contract tests, 1 new router test), purity still green. Did not touch the Weighing form, load-sequence engine, RLS, session/test flow, or the other test forms. Updated `docs/architecture.md` (Database schema: the 21 new columns + the additive-migration note referencing ADR-0007; Frontend: the Instrument Registration rewrite and the shared `FormPrimitives` extraction) and its STATUS line.

**Next:** Verify on the preview deploy (checklist in the branch reply) — the operator must run `db/migrations/002_registration_fields.sql` against the live Supabase project before the new fields will persist there; without it, `POST /api/instruments` will 500 on any request that includes them (an unrecognized column), though the core fields (identity + e/Max/Min) will keep working exactly as before since those columns already exist. Then: the per-session test selector (Phase 3); the session/selection update endpoint; submit-for-review/approve/return; PDF; verify page.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification (per-sub-range e/n/Min) is a known future extension — not handled by `classify_instrument`, same limitation as `load_sequence`.
- Multi-interval page-6 sub-ranges (e1/Max1/d1/n1 and beyond) have no schema column yet — rendered blank on the form for now.
