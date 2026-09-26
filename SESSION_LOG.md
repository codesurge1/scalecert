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
