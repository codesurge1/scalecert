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

---

### [2026-09-26] — fix: remove forced test sequence - tests run in any order

**Investigated a reported forced-sequence bug — found none in the current code.** RRSL (Deputy Director Sharma) confirmed tests are technician-selectable in any order, no fixed sequence, matching `docs/plan.md`'s own per-session-test-selector requirement ("Tests run in any order"), and the task asked to strip any cross-test-status gating from the session overview. Audited every place a test's availability is decided: `src/lib/testChecklist.js` (`isSelectable`), `src/components/session/AddTestDialog.jsx`, `src/pages/SessionPage.jsx`, `src/pages/WeighingSessionPage.jsx` on the frontend, and `app/routers/sessions.py`, `app/routers/instruments.py`, `app/services/sessions.py` (`ensure_session_is_draft`), `app/repositories/{sessions,readings}.py` on the backend. Found no logic anywhere that conditions one test's availability on another test's status (not-started/in-progress/complete) — `isSelectable` already takes only `(row, instrument)`, never session/reading/progress state; the only two gates present were already the two legitimate ones this task explicitly says to keep: (1) applicability (`naReason`, driven by instrument properties) and (2) not-yet-implemented (`row.key !== "weighing"`, since the other six tests have no form built yet, always labeled "Coming soon"/"N/A", never "complete X first"). The only status check anywhere in the flow is `ensure_session_is_draft` — a session-lifecycle gate (readings rejected once a session leaves `draft`), not a cross-test ordering rule; it stays, per the task's own instruction that draft-status checks aren't sequencing.

**Hardened against future regression rather than leaving it implicit.** Since there was no bug to remove, the change is defensive documentation + comments, so the "any order" guarantee can't silently erode as the other six tests get real forms in later tasks: added an explicit comment block above `isSelectable` naming its two legitimate gates and stating its signature (`row`, `instrument` only) is deliberately shaped to make a sequence dependency impossible to add without changing the function's contract; added matching "no forced sequence" notes to `AddTestDialog.jsx`'s and `SessionPage.jsx`'s own docstrings; added a new bullet to `docs/architecture.md`'s Navigation section stating the guarantee explicitly, citing the RRSL finding, and naming exactly which two gates are legitimate and why the backend's one status check isn't a third.

`npm run build` succeeds (720.48 kB bundle, unchanged). Full suite: **275 passed** (unchanged — no backend ordering check existed to remove, so no test additions were needed; every existing test still passes). Did not touch the Weighing form, the engine, RLS, applicability rules, or the schema, per the task's explicit scope limits.

**Next:** Verify on the preview deploy (checklist in the branch reply) that the Add-test picker and session overview behave identically to before for the one real test (Weighing) — this task changed no runtime behavior, only comments/docs, so there should be zero visible difference. When the per-session test selector (`docs/plan.md` Phase 3) eventually gives the other five test_types real forms and `session_test_selection` rows, `isSelectable`'s (row, instrument)-only signature is the guardrail to preserve — any change that threads in session/progress state to compute selectability should be treated as a regression of this task's finding, not a feature.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification (per-sub-range e/n/Min) is a known future extension — not handled by `classify_instrument`, same limitation as `load_sequence`.
- Multi-interval page-6 sub-ranges (e1/Max1/d1/n1 and beyond) have no schema column yet — rendered blank on the form for now.

---

### [2026-09-26] — feat: Zero/tare, Repeatability, and Eccentricity test forms

**Done — engine, built and tested first, as instructed.** Read R76-2 pages 12 (Eccentricity) and 16 (Repeatability) as rendered images — both readable, both matched the design before any code was written. Three new pure modules, each its own structure, not a Weighing clone:
- `engine/zero_tare.py` — thin wrapper delegating to `compute_weighing_result` (identical math), plus `generate_zero_tare_checks` (3 deterministic check loads: 0, an anchor from `min_capacity` or a documented fallback fraction of Max, and 2× that anchor) — no Table-6-anchored sequence, "a few readings," never technician-entered `L`.
- `engine/repeatability.py` — genuinely new function, `compute_repeatability_series`: two series at fixed loads (`generate_repeatability_load`: ~50%/100% of Max), NO E0 (E checked directly against mpe, per the real page-16 form having no Ec column), two independent per-series criteria (every reading `|E| <= mpe`, AND spread `Emax − Emin` using SIGNED E `<= mpe`) — takes the whole series' readings at once, since spread is a whole-set property.
- `engine/eccentricity.py` — thin wrapper, `compute_eccentricity_position`: same Weighing math, but E0 is supplied fresh per position (no shared baseline) and `generate_eccentricity_load` derives one fixed load (~1/3 Max, documented convention) shared across all 4 positions.

New dataclasses (`RepeatabilityReadingResult`, `RepeatabilitySeriesResult`, `EccentricityPositionResult`) added to `engine/types.py`, matching the existing centralized-dataclasses convention. `tests/test_zero_tare.py` (18 tests), `tests/test_repeatability.py` (24 tests), `tests/test_eccentricity.py` (11 tests) — boundary cases at the mpe edge (inclusive) for both individual and spread criteria, a case proving the two series get genuinely different mpe (not coincidentally equal), proof that E is signed not abs'd for spread, E0-independence-per-position, and delegation-equality checks against `compute_weighing_result`. Two real bugs caught by these tests before anything else was built on top: a `Decimal("1")/Decimal("3")` precision artifact in the eccentricity load (fixed to direct division), and test fixtures that forgot the `delta_l = e/2` cancellation trick (test-only, not an engine bug). Purity green throughout — new engine files import only `engine.*` and stdlib.

**Done — backend.** Three new contract modules (`app/contracts/{zero_tare,repeatability,eccentricity}.py`) following `weighing.py`'s shape, each trimmed/extended to its own test's actual fields (no `direction` on zero_tare/repeatability, no `E0`/`Ec` at all on repeatability, `position_no`-keyed on eccentricity with per-position `E0` as real input). Three matching pure service modules (no DB/HTTP) mirroring `services/weighing.py`. `app/repositories/readings.py`'s `insert_reading`/`insert_result` generalized to take `test_type` (now required, no more hardcoded `"weighing"`) and optional `series_no`/`position_no` — the existing Weighing call sites in `routers/sessions.py` updated to pass `test_type` explicitly, zero behavior change. Nine new routes on the existing `/sessions` router (checks/readings×3 for zero-tare, readings×2 for repeatability, setup/readings×3 for eccentricity), reusing the hardened `RepositoryError`→403/500 mapping, the draft-only write check, and the reading+result-together-with-rollback pattern verbatim — no new error-handling code paths invented. Zero/tare readings are stored under `test_type='weighing'` (no new enum value — the schema already anticipated this in its own enum comment) and distinguished from a real Weighing-sequence reading by `direction` being null vs. set; no schema, RLS, or Weighing-behavior change anywhere. `backend/tests/services/test_{zero_tare,repeatability,eccentricity}_service.py` (17 tests) and `backend/tests/routers/test_{zero_tare,repeatability,eccentricity}_router.py` (26 tests) — happy paths, 404/409/422s, rollback-on-result-failure, dedup-to-latest, and (repeatability-specific) that a submission's response reflects the WHOLE series including previously-stored readings, not just the new one.

**Done — frontend.** Three new bordered-document-sheet forms (`ZeroTareFormTable`/`RepeatabilityFormTable`/`EccentricityFormTable`, reusing the shared `FormPrimitives`) and their session pages, each genuinely reproducing its own source page's layout rather than reskinning Weighing's: Zero-tare is a small single check-load table with no ↓/↑ columns; Repeatability is two side-by-side 10-row tables with a Load box and Emax−Emin/mpe boxes per series, E-only columns (no Ec), and one shared Passed/Failed pair requiring both series; Eccentricity has the page-12 position sketch (2×2 grid, clockwise) and a 4-row table with a per-row E0 input. `testChecklist.js`'s `TEST_ROWS` gained a `route(sessionId)` function per implemented row; `isSelectable` now checks "has a route" instead of hardcoding `key === "weighing"` — its `(row, instrument)`-only signature (the no-forced-sequence guardrail from the previous task) is unchanged. `SessionPage.jsx` now lists all four implemented tests with independently-computed live status (a new shared `computeProgress` helper) instead of just Weighing — none of the four reads another's status, and none needs a `session_test_selection` row to show correctly.

`npm run build` succeeds (750.38 kB bundle). Full suite: **369 passed** (was 275 — 53 new engine tests, 17 new service tests, 26 new router tests), purity still green. Did not touch the Weighing form's own behavior, the engine's existing modules, RLS, applicability rules for Discrimination/Tilting/Sensitivity, or the schema. Updated `docs/architecture.md` (Engine: three new subsections; Contracts: the three new modules; Database schema: how the pre-existing `direction`/`series_no`/`position_no` columns are now actually used; API surface: nine new routes; Frontend: the three new forms/pages, the overview's four-test status table, and the "Not built here" list trimmed to just Discrimination/Tilting/Sensitivity) and its STATUS line.

**Next:** Verify on the preview deploy (checklist in the branch reply) — in particular that the zero/tare `direction IS NULL` discriminator actually round-trips correctly against real Postgres (this sandbox's mocked tests can't prove a `null` filter behaves as expected against PostgREST). Then: Discrimination/Tilting/Sensitivity (the last three checklist items); the per-session test selector (Phase 3); submit-for-review/approve/return; PDF; verify page.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Zero/tare check-load anchor (min_capacity or 5% of Max fallback) and Eccentricity's ~1/3-Max load are both documented conventions, not OIML-sourced figures — pending RRSL confirmation, same status as Band-1 spacing.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-26] — feat: Discrimination, Tilting, Sensitivity - all 7 checklist tests complete

**Done — engine, built and tested first, as instructed.** Read R76-2 pages 14 (Discrimination), 15 (Sensitivity), and 20 (Tilting) as rendered images — all three readable, all three matched the design before any code was written. Three new pure modules:
- `engine/discrimination.py` — THREE genuinely distinct sub-procedures (not variants of one formula): `compute_discrimination_analog` (I2−I1 ≥ 0.7·mpe), `compute_discrimination_non_self_indicating` (purely qualitative — passed IS the observed boolean), `compute_discrimination_digital` (I2−I1 ≥ d, no mpe/accuracy_class/verification_type at all — implemented per A.4.8.2 for spec completeness even though clause 8.3.3 doesn't require it for digital instruments; the frontend keeps the whole test N/A for digital, so this sub-procedure is engine/API-reachable only, never through normal navigation).
- `engine/sensitivity.py` — `sensitivity_threshold_mm`, tiered by accuracy class AND Max (1mm class I/II; 2mm class III/IIII ≤30kg; 5mm class III/IIII >30kg) — `MAX_THRESHOLD_GRAMS=30000` compared directly since max_capacity is stored in grams.
- `engine/tilting.py` — the minimal 8.3.3/4.18 slice (reference + 4 tilted positions × unloaded/mid-load/Max), not the full Annex A.5.1 battery. Reuses `compute_weighing_result` entirely (unloaded reading = L=0,E0=0 call; loaded reading = that position's own E0 as input) rather than reimplementing the formula. Two aggregation functions mirror Repeatability's whole-set-property shape: `compute_tilting_unloaded_check` (|E1,0−Ev,0|max ≤ 2e) and `compute_tilting_loaded_check`, checked independently per loaded row so the two loads can (and do, per a dedicated test) land in different Table 6 bands.

New dataclasses added to `engine/types.py` (`DiscriminationAnalogResult`, `DiscriminationNonSelfIndicatingResult`, `DiscriminationDigitalResult`, `SensitivityResult`, `TiltingUnloadedCheckResult`, `TiltingLoadedCheckResult`). `tests/test_discrimination.py` (23 tests), `tests/test_sensitivity.py` (17 tests), `tests/test_tilting.py` (18 tests) — every mpe/threshold/limit boundary inclusive on both sides, the 30kg tier boundary tested both sides explicitly, E0-measured-once-per-position-and-reused proven directly against a bare `compute_weighing_result` call, and a genuinely-differing-mpe case for Tilting's two loaded rows (same proof pattern Repeatability established). Purity green throughout.

**Done — backend.** `InstrumentParams` (`app/contracts/instrument.py`) extended with `indication_type`/`is_mobile`/`d_value` (purely additive — updated the four existing test fixtures that constructed it directly, plus one contract test missing the new required row keys). Three new contract modules following the established per-test shape, with one deliberate structural choice: `discrimination.py` uses ONE submit-in model with all variant-specific fields `Optional`, the applicable variant derived server-side from `instrument.indication_type` (never client-chosen, same discipline as accuracy_class) — `app/services/discrimination.py` enforces which fields that derived variant actually needs, raising `MissingFieldsForVariant` (→422) otherwise. `app/repositories/readings.py` needed no further changes (already generalized last task). Nine new routes on the existing `/sessions` router: Discrimination/Sensitivity mirror the Zero-tare checks/readings/readings shape exactly; Sensitivity's and Tilting's POSTs add a genuine server-side applicability check (422 if `indication_type != non_self_indicating` / `not is_mobile`) — defense in depth alongside the frontend's own N/A gating, same principle as accuracy-class derivation. Tilting reuses `sequence_no` to encode phase (0/1/2 for unloaded/mid-load/Max, since the column is `not null` and Tilting has no real sequence) alongside `position_no` for the tilt position — no schema change, every column and enum value (`discrimination`/`tilting`/`sensitivity`) was already present from ADR-0005's original schema. One real bug caught by router tests before merge: Tilting's POST route initially re-fetched readings from the DB *after* inserting, which a mocked test correctly caught as not reflecting the just-submitted reading — fixed to match Repeatability's own pattern (fetch existing readings, merge the new submission in locally, compute once) rather than depending on read-after-write timing. `backend/tests/services/test_{discrimination,sensitivity,tilting}_service.py` (29 tests) and `backend/tests/routers/test_{discrimination,sensitivity,tilting}_router.py` (30 tests) — all three sub-procedures exercised end-to-end through the API, both applicability gates, dedup-to-latest, rollback-on-result-failure, and (Tilting-specific) that a submission's response reflects previously-stored readings too, not just the new one.

**Done — frontend.** Three new bordered-document-sheet forms and their session pages, each faithful to its own source page: `DiscriminationFormTable` renders only the ONE sub-table matching the instrument's derived variant (analog/non-self-indicating/digital genuinely differ in columns, not just labels); `SensitivityFormTable` prints the standard's three-tier text with the tier that actually applies to this instrument bolded; `TiltingFormTable` is three stacked 5-column (reference + 4 tilted) mini-tables (unloaded/mid-load/Max) with the two aggregate-check boxes below each, and — like `RepeatabilityFormTable` — replaces its entire local state with the fresh server-recomputed state after every submission, since Tilting's pass criteria are whole-dataset properties. `testChecklist.js`'s three remaining rows (Discrimination/Tilting/Sensitivity) gained `route(sessionId)` while keeping their existing `naReason` functions completely unchanged — applicability logic didn't need to change, only "is there a form to route to" did. `SessionPage.jsx` now renders all seven `TEST_ROWS` (not a filtered subset): a row with a truthy `naReason` shows "N/A" and no button, every other row shows live status — extending the exact same `computeProgress` pattern the previous task established, no new pattern invented for these three.

`npm run build` succeeds (780.83 kB bundle). Full suite: **477 passed** (was 369 — 58 new engine tests, 29 new service tests, 30 new router tests), purity still green. Did not touch the four existing tests' behavior, RLS, or the schema (every column/enum value needed already existed). Updated `docs/architecture.md` (Engine: three new subsections; Contracts: the discrimination-variant design decision and the `InstrumentParams` extension; Database schema: how `sequence_no`/`position_no` are now also used by Discrimination/Sensitivity/Tilting; API surface: nine new routes, including the two server-side applicability gates; Frontend: the three new forms/pages, all-seven-rows overview, and the "Not built here" list now free of any checklist test) and its STATUS line.

**Next:** Verify on the preview deploy (checklist in the branch reply) — in particular the two server-side applicability 422s (Sensitivity on a non-non-self-indicating instrument, Tilting on a non-mobile one) against real Postgres-backed instrument rows, and that Tilting's `sequence_no`-as-phase encoding round-trips correctly. After this: submit-for-review/approve/return, PDF (can likely reuse every form's exact visual layout), the public verify page, and — much later — the real per-session test selector (Phase 3) so every test_type gets a genuine `session_test_selection` row instead of status derived purely from readings.

**Open questions:**
- Band-1 intermediate load spacing, the zero/tare check-load anchor, Eccentricity's ~1/3-Max load, and now Tilting's ~50%-Max mid load and Discrimination/Sensitivity's 3-point check-load anchors — all documented conventions, not OIML-sourced figures, pending RRSL confirmation.
- Tilting's "(not valid for class II instruments, if not used for direct sales to the public)" carve-out is not modeled — no direct-sale flag exists on a registered instrument. Flagged in the form's own caption, not silently dropped.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: round load-sequence fills and display precision

**Done — Problem 1 (engine).** `engine/load_sequence.py`'s Band-1 fill strategy no longer spaces fills by raw fractional division (`span * i / (count+1)`, which produced values like `885.714285714285714285714286`). New `_nice_step_at_or_below(raw_step)` finds the largest "nice" 1/2/5 × 10^k step ≤ a raw value — by scanning a power-of-ten scanner up/down and multiplying it by 5/2/1, never dividing `raw_step` itself, so the result is always an exact Decimal. New `_round_fill_points_within_band_1` (replaces `_even_spacing_within_band_1`) derives one step from the same ideal spacing the old formula used (`span/(count+1)`), snaps it down to the nearest nice value (guaranteeing at least as many candidates fit), builds the full list of that step's multiples inside Band 1 excluding anchors, then — if more candidates exist than needed — picks `count` of them at evenly-spaced list indices (Decimal `ROUND_HALF_UP`, never float division) so fills stay spread across the band rather than clustering low, with a top-up fallback for the rare index-rounding collision that could otherwise under-fill by one. Anchors (Max, Min, band transitions) are completely untouched — only fill points changed. `FILL_SPACING_STRATEGY` renamed to `"round_step_spacing_within_band_1"`. For the demo instrument (e=10, Max=30000, Min=200): fills are now `{500, 1500, 2000, 3000, 3500, 4500}` — all round whole numbers, matching real test weights, instead of a repeating-decimal fraction.

**Done — Problem 1 (engine tests).** Extended `test_typical_class_iii_instrument_reaches_target_of_ten` with explicit anchor/fill-value assertions and a whole-number check per fill. Added 5 new tests: fills are round whole numbers not repeating decimals; fills never collide with or duplicate anchors; fills stay strictly inside Band 1; the round-fill strategy still reaches the target of 10 when the whole range is Band 1; determinism (same inputs → identical `L` values, run twice). All pre-existing tests passed against the new logic unchanged.

**Done — Problem 2 (frontend).** New shared helper `frontend/src/lib/displayFormat.js` (`roundForDisplay(value, decimals=2)`, `roundLoadForDisplay` = alias for `decimals=1`) — `Number()`/`toFixed()`-based, safe specifically because the output is display-only, thrown away after rendering, never fed back into a request or component state used for submission; the exact Decimal-as-string the backend returns is untouched everywhere else. Wired into all 7 test-table components (`WeighingFormTable`, `ZeroTareFormTable`, `RepeatabilityFormTable`, `EccentricityFormTable`, `DiscriminationFormTable` — all three variant sub-tables, `SensitivityFormTable`, `TiltingFormTable`): every computed result field (`E`, `Ec`, `mpe`, margin/spread/difference/threshold/extra-load) goes through `roundForDisplay`, every derived/generated load (`L`, `setup.L`, series `L`, tilting `L`/`max_capacity`) through `roundLoadForDisplay`. Found and fixed several plain (non-`fmt`-wrapped) numeric interpolations the initial grep missed — `entry.L`/`entry.mpe` in Weighing's main table, `check.L` in Zero-tare/Discrimination/Sensitivity, `check.extra_load` in Sensitivity — all now wrapped too. Identity/text fields (`application_no`, `type_designation`, the instrument's own registered `e_value`/resolution) stay on the existing plain-passthrough local `fmt()`, deliberately unrounded since they're not computation results. `SensitivityFormTable`'s `thresholdMm` keeps its raw string value for the `=== "1"`/`"2"`/`"5"` tier-comparison logic; only the final display call site is rounded (to 0 decimals, since it's a discrete tier value, not an error figure — `roundForDisplay(thresholdMm, 0)`).

`npm run build` succeeds. Full suite: **482 passed**, `tests/test_purity.py` still green (`ROUND_HALF_UP` is a stdlib `decimal` import). Did not touch `backend/`, `db/schema.sql`, or any RLS policy. Updated `docs/architecture.md` (Engine: rewrote the Band-1 fill-spacing paragraph to describe round-step snapping instead of even fractional spacing; Frontend: new paragraph on `displayFormat.js` as the presentation-only rounding layer, explicit that it never touches the Decimal-as-string discipline already documented there).

**Next:** No further action from this task — display rounding is now uniform across all seven test forms and the load sequence reads like a real report. If RRSL ever confirms an actual fill-spacing convention, `FILL_SPACING_STRATEGY` is still the one place to change it (now naming the round-step approach). A future task could reconsider `roundForDisplay`'s default 2-decimal precision per-field (e.g. matching each instrument's own `e`) if a real report reviewer asks for it — not done here since the task scoped a "clean, sensible" fixed precision, not per-instrument dynamic precision.

**Open questions:**
- Band-1 intermediate load spacing is still a documented placeholder pending RRSL confirmation — only its snapping mechanism changed (round-step instead of raw fraction), not its "pending confirmation" status.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: prepend 10e load to weighing sequence (RRSL convention)

**Done.** Added a new mandatory anchor to `engine/load_sequence.py`'s Weighing load sequence: the run now starts at ten verification scale intervals (`10 * e`, new `TEN_E_START_MULTIPLE` constant), matching the RRSL lab convention of never applying the first test load below that point. Tagged with a new `LoadKind.TEN_E` (`engine/types.py`) — distinct from the three OIML-sourced anchor kinds (`max`/`min`/`band_transition`) and from `fill`, explicitly labeled in both modules' docstrings as a mandatory-but-not-OIML-sourced convention, same "pending RRSL confirmation" framing as `FILL_SPACING_STRATEGY`. `LoadEntry.is_anchor` needed no logic change — it was already "true for everything except `fill`" — only its docstring was updated to name the new kind explicitly. Three edge cases handled via the existing anchor machinery, not new logic: skipped outright if `10e > Max` (a tiny-range instrument — no clamping to Max); deduped via the existing `seen_L` mechanism if `10e` lands exactly on an already-claimed anchor (added after Max/Min, before band transitions, so an OIML-sourced anchor — most commonly Min, on an instrument where `Min == 10e` — always wins that tie over the convention anchor); and it counts toward `MIN_VERIFICATION_LOAD_COUNT` like every other anchor, so `needed = MIN_VERIFICATION_LOAD_COUNT - len(anchors)` (unchanged) automatically absorbs it — one fewer fill is generated per 10e anchor actually added, keeping the total at the target of 10 rather than growing to 11. Nothing else in the generator changed: Band-1 fill logic, `lower_bound`, sourced-anchor logic, and dedupe semantics are byte-for-byte the same as before this task.

For the demo instrument (e=10, Max=30000, Min=200): the sequence is now `TEN_E(100), MIN(200), FILL(1000), FILL(1500), FILL(2500), FILL(3500), FILL(4000), BAND_TRANSITION(5000), BAND_TRANSITION(20000), MAX(30000)` — 5 anchors + 5 fills = 10 total (previously 4 anchors + 6 fills), with 100 as the new first/lowest load.

**Tests.** `tests/test_load_sequence.py`: updated four existing tests whose anchor/fill counts shift now that a 5th (or 2nd) anchor exists for their fixtures (`test_fills_added_to_reach_minimum_count`, `test_typical_class_iii_instrument_reaches_target_of_ten` — including the demo instrument's now-updated fill set and an explicit `loads[0] == 100` check, `test_round_fill_still_reaches_target_when_whole_range_is_band_1`, `test_fills_are_round_whole_numbers_not_repeating_decimals`); every other pre-existing test either collides 10e with Min (dedupes, no count change) or asserts generically enough to need no change. Added 4 new tests: `test_ten_e_is_the_first_load` (demo instrument, lowest load = 100, tagged `TEN_E`), `test_ten_e_dedupes_when_equal_to_min` (e=1, Min=10 → 10e=10=Min exactly: one entry, kind stays `MIN`, no `TEN_E` entry, anchor count unaffected), `test_ten_e_skipped_when_it_would_exceed_max` (e=10, Max=50 → 10e=100>50: no `TEN_E` entry anywhere, no load above Max, sequence still reaches 10 via Max+fills alone), `test_ten_e_is_deterministic`. Full suite: **486 passed** (was 482 — 4 new tests, no regressions), `tests/test_purity.py` still green (only a new stdlib-Decimal constant and enum member, no new imports). Did not touch `backend/`, `frontend/`, display rounding, or any other test's engine module — confirmed no frontend code renders/switches on `LoadKind` values today (the earlier `KindBadge` component was removed in a prior session when `WeighingFormTable` replaced the old `LoadSequenceTable`), so the new kind needed no form-component change.

Updated `docs/architecture.md`'s load-sequence section: a new bullet describing the 10e-start convention (mandatory anchor, not OIML-sourced, dedupe/skip edge cases, demo-instrument numbers) placed between the sourced-anchors bullet and the Band-1 fill-spacing bullet; updated the fill-spacing bullet's closing sentence to name `ten_e` as a third `LoadKind` category alongside the three sourced kinds and `fill`.

**Next:** No further action from this task. If RRSL ever confirms this isn't the right start-load convention (e.g. a different multiple of e, or a fixed gram value instead), `TEN_E_START_MULTIPLE` is the one constant to change.

**Open questions:**
- Band-1 intermediate load spacing is still a documented placeholder pending RRSL confirmation, unchanged by this task.
- The 10e start-load convention itself is now implemented but, like the fill-spacing convention, still pending final RRSL confirmation that 10e (rather than some other multiple or fixed value) is the right anchor.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — feat: session lifecycle — submit, approve, return, issue

**Done — backend.** Five new endpoints on the existing `/sessions` router (`app/routers/sessions.py`): `POST /sessions/{id}/submit` (creator only, `draft → submitted`, sets `submitted_at`, rejects with 409 if the session has zero recorded readings across every test — `readings_repo.has_any_reading`, no test_type filter); `POST /sessions/{id}/reopen` (creator only, `returned → draft` — **not one of the task's four named transitions**, added because nothing else moves a session out of `returned`: `readings_write`'s RLS policy requires `status='draft'` before any reading can be edited, so this is what actually makes "returned → technician edits → resubmits" possible); `POST /sessions/{id}/return` (approver/admin, not own session, `submitted → returned`, required `reason` — stored ONLY in `audit_log.data.reason`, no `test_sessions` column added; this is the one audit write in the whole app that is deliberately NOT non-fatal and is written BEFORE the status update, since losing it would silently discard the only copy of the reason); `POST /sessions/{id}/approve` (approver/admin, not own session, `submitted → approved`, sets `approved_by`/`approved_at` — the core separation-of-duties action); `POST /sessions/{id}/issue` (approver/admin, not own session, `approved → issued`, sets `issued_at` and `certificate_number` — restricted further to an admin OR specifically the SAME approver who approved, `ensure_can_issue`, a deliberate documented choice since RLS itself has no notion of "the same approver").

Separation of duties enforced twice, per CLAUDE.md: RLS (`sessions_update_owner`/`sessions_update_approver`, unchanged) is the coarse, non-negotiable guard — an approver acting on their own session matches neither policy and fails with `42501`; the API layer adds its own explicit checks (`app/services/sessions.py`: `ensure_is_creator`, `ensure_is_approver_or_admin`, `ensure_not_own_session`, `ensure_can_issue`, all pure and unit-tested) BEFORE any DB write, so a rejection is a specific message ("cannot approve: separation of duties — you cannot approve a session you created yourself") rather than a bare RLS 403. Out-of-order transitions (`ensure_status`) are a clean 409, deliberately narrower than what RLS itself would technically allow (`sessions_update_approver`'s `USING` clause permits `status in ('submitted','returned','approved')` for any approver-role UPDATE) — the API layer is where finer transition validity is actually enforced, per the schema's own comment beside that policy.

**Certificate-number assignment (ADR-0008).** The only schema change in this task: one small `SECURITY DEFINER` function, `public.issue_certificate_number()` (`db/schema.sql`), consuming `certificate_number_seq` atomically and formatting `SC-{YEAR}-{6-digit}` — added because PostgREST's REST-only surface has no way to call `nextval()` on a bare sequence from the JWT-scoped client (never the service-role key), and the task explicitly requires assignment "from the certificate_number_seq sequence," which pure application-side counting can't guarantee atomically. The function's own role check (`get_my_role() NOT IN ('approver','admin') → RAISE EXCEPTION ... ERRCODE '42501'`) is defense in depth alongside the API's own checks. Called via a new `run_rpc` helper (`app/repositories/errors.py`, symmetric to `run_select`/`run_insert`) — the same `APIError`→`RepositoryError` translation applies to an RPC call that itself raises. A wasted/skipped sequence number if the RPC succeeds but the subsequent session UPDATE then fails is an accepted, standard consequence of using a Postgres sequence (never rolled back by a later failure) — documented, not treated as a bug. Fixed a now-stale CLAUDE.md guardrail line in the same commit ("assigned at approval time" → "assigned at issue time, always after approval") — code-wins rule.

Also added: `run_update` (`app/repositories/errors.py`, symmetric to `run_insert` — a zero-row UPDATE result means the row's current state didn't satisfy the policy's `USING` clause); `app/repositories/profiles.py` (new — `get_role`, reusing the same `profiles_select_own` RLS clause `/whoami` already relies on to reliably read the CALLER's own role); `sessions_repo.update_session`/`get_latest_return_reason`/`issue_certificate_number`; `readings_repo.has_any_reading`. `SessionOut` (`app/contracts/session.py`) extended with `submitted_at`/`approved_by`/`approved_at`/`issued_at`/`certificate_number` (straight from the row, all `None` until their transition) and `return_reason` (NOT a column — populated only when the session is currently `returned`, via `_build_session_out`'s helper in the router, so every other status skips that extra read); new `SessionReturnIn` (required, 1–2000 char `reason`).

**Done — frontend.** New `SessionLifecyclePanel` (`src/components/session/SessionLifecyclePanel.jsx`) on the session overview (`SessionPage.jsx`), gated by the caller's own role/id (`useProfile`, reused from `AppShell.jsx`) and the session's current status: a status stepper (Draft → Submitted → Approved → Issued, with `returned` shown as a distinct warning-colored detour off Submitted rather than forced onto the linear line); the return reason shown inline when `returned`; "Submit for review" (technician, draft, disabled with an inline reason until at least one test has recorded progress — a friendlier client-side echo of the server's own 409, not a replacement for it); "Reopen for editing" (technician, returned); "Approve"/"Return" (approver/admin, submitted, not their own session — a `ReturnSessionDialog` with a required textarea for the reason) or, for an approver viewing their OWN submitted session, an explanatory note instead of buttons ("You cannot approve your own session (separation of duties)..."); "Issue certificate" (approver/admin, approved, gated further to admin-or-the-approving-approver, mirroring `ensure_can_issue`) or an explanatory note otherwise; the certificate number, once issued, as a prominent green badge next to the stepper. Every action is a plain `POST` with no body except `/return`, using the existing `apiFetch`/toast conventions (`StartVerificationDialog.jsx`'s pattern) — a rejected call (e.g. a stale-tab race hitting a 409) surfaces the server's own clean message via `toast.error`, never a silent failure. Did not touch any of the 7 test-form components or their session pages: all already gate on `sessionStatus !== "draft"` (`disabled` on every input) and already show a "not draft — read-only" banner — flipping `session.status` via these new endpoints is sufficient by itself to make them read-only (submit) or editable again (reopen), confirmed by re-reading all 7, not assumed.

`npm run build` succeeds. Full suite: **541 passed** (was 486 — 16 new `app.repositories.errors` unit tests for `run_update`/`run_rpc`, 25 new `app.services.sessions` unit tests, 14 new/updated `app.contracts.session` tests, 45 new `app.routers.sessions` lifecycle-transition tests, 10 pre-existing router tests otherwise unaffected), `tests/test_purity.py` still green (no engine changes at all this task). Updated `docs/architecture.md` (Database schema: certificate-numbering paragraph now says "at issue," not "at approval"; Session lifecycle: the five endpoints, the twice-enforced separation of duties, the out-of-order-transition guard, the lifecycle trail on `SessionOut`; API surface: the five new routes; STATUS line; "Not built here" narrowed to PDF + public verify only) and `CLAUDE.md`'s stale "assigned at approval time" guardrail. Added ADR-0008 for the one schema change (`issue_certificate_number()`).

**Next:** Verify on the preview deploy — the full separation-of-duties demo end to end (see the branch reply's "verify on preview" list): a technician submits, logs out, an approver logs in and sees Approve/Return, approves, issues, the certificate number appears; and that an approver who happens to BE the session's creator sees the explanatory note instead of buttons, never a way to bypass it. Then: PDF generation (can now pull `certificate_number`/`approved_at`/`issued_at` directly from `SessionOut`) and the public verify page (`certificate_number` → session lookup) are the two remaining pieces this task deliberately left out. Superseding an issued session (`supersedes_session_id`) and the per-session test selector (Phase 3) remain later, unrelated refinements.

**Open questions:**
- Whether "the same approver who approved, or an admin" is the right issue-authorization rule long-term, or whether RRSL would prefer any approver/admin to be able to issue — a deliberate, documented choice (docs/architecture.md, Session lifecycle) that's easy to relax in one place (`ensure_can_issue`) if RRSL disagrees.
- "Who approved" is shown as a shortened UUID, not a resolved name — no profile-name-lookup route is exposed to every viewer under current RLS (a technician can only see their own profile row), and adding one was out of this task's scope.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — feat: PDF certificate generation and public verification page

**Done — Part A, PDF generation.** `POST /api/sessions/{id}/report` (`app/routers/sessions.py`) — approver/admin OR the session's own creator (not separation-of-duties-sensitive, unlike approve/return/issue), only when `status == 'issued'` (409 otherwise). Built with `reportlab` (new dependency, `backend/requirements.txt`), entirely in-memory (`io.BytesIO` — never local disk). Split cleanly for testability: `app/services/certificate.py` (pure — no DB, no reportlab) assembles a `CertificateData` from already-fetched rows/service outputs; `app/pdf/certificate.py` (reportlab only, no DB) renders it. Weighing gets its full load/I/ΔL/E/Ec/mpe/pass-fail table (the checklist's priority item, per the task's own scoping); every other test performed gets a one-line PASS/FAIL/Incomplete summary, each computed the RIGHT way for that test — Zero-tare/Eccentricity/Discrimination/Sensitivity have no whole-set criterion so "all readings' own stored `passed`" is correct; Repeatability and Tilting are recomputed via `repeatability_service.compute_series`/`tilting_service.compute_state` (the SAME functions their own GET routes call), not a naive per-reading scan, since a naive scan would silently miss Repeatability's spread criterion and Tilting's per-reading `passed` is always `None` by design. The QR code (reportlab's own built-in `graphics.barcode.qr`, no second dependency) encodes the FULL public verify URL, built from `request.base_url` with an optional `PUBLIC_APP_BASE_URL` override. Stored to the `reports` bucket at a deterministic `certificates/{certificate_number}.pdf` key (`app/repositories/storage.py`, `upsert` so regenerating is idempotent) via the caller's own user-scoped client — never service-role — flagged as an assumption about the bucket's own Storage policies that's genuinely unverified until the next real deploy. The PDF bytes are returned directly in the response (`Content-Disposition: attachment`), not a signed URL.

**The one real wrinkle: `report_storage_path` can't be set with a plain `.update()`.** An `issued` session matches NO UPDATE policy on `test_sessions` at all (by design, so a certificate's content can never change) — including for this one bookkeeping column. Solved with a THIRD small `SECURITY DEFINER` function, `public.set_report_storage_path(p_session_id, p_path)` (db/schema.sql, ADR-0009), following ADR-0008's exact precedent: it re-checks the session is `issued` and the caller is the creator or an approver/admin, then updates only that one column — it does not reopen general mutability of an issued row. The write is deliberately non-fatal if it fails (logged, not raised): unlike a return-reason, the path is fully deterministic from `certificate_number` alone, so nothing is lost.

**Done — Part B, public verification.** The ONE part of this API with no `Depends(get_auth_context)` at all: `GET /api/verify/{certificate_number}` and `POST /api/verify/{certificate_number}/report-discrepancy` (new `app/routers/verify.py`), using `app.supabase_client.anon_client()` (pre-existing, unused before this task) — never service-role, never a per-request user-scoped client, since there's no user to scope to. `public.get_public_certificate_info(p_certificate_number)` (db/schema.sql) is the ONE deliberate anonymous-read exception in the whole schema — a `SECURITY DEFINER` function returning exactly `certificate_number`/`status`/`instrument_model`/`instrument_manufacturer`/`instrument_type_designation`/`accuracy_class`/`verification_type`/`issued_at`, gated by its own `WHERE status = 'issued'` clause: a nonexistent number and a real-but-not-issued one both come back as zero rows, indistinguishably — the API can never leak which. `app.contracts.verify.PublicCertificateOut` mirrors this exact field list with `extra="forbid"`, so a future accidental `SELECT` addition would need an equally deliberate model change, never silently pass through. New `discrepancy_reports` table (`id`, `certificate_number`, `description`, `contact`, `created_at`, no FK) with a single-purpose RLS policy (`discrepancy_insert_anon ... with check (true)`, no matching anonymous SELECT — only `admin` can ever read them back) rather than a third function, since a plain unconditional insert doesn't need one. Deliberately does NOT validate that `certificate_number` is real/issued before accepting a report — validating would itself create the exact leak the GET route is careful to avoid (distinguishing "real but not issued" from "doesn't exist"). No rate-limiting: a correct implementation needs durable cross-invocation state, which an in-process limiter cannot provide on Vercel's stateless functions — noted as a follow-up, not built.

**New repository-layer helpers, each with a genuinely different RPC return-shape contract** (`app/repositories/errors.py`): `run_rpc_list` (a `RETURNS TABLE` function where an empty list is a VALID outcome — `get_public_certificate_info`) and `run_rpc_void` (a `RETURNS void` function with no `.data` to check at all — `set_report_storage_path`), siblings to the existing `run_rpc` (scalar return, empty IS an error — `issue_certificate_number`) — three small helpers instead of one flag-driven do-everything function, since each function's own return contract genuinely differs. Also new: `app/repositories/public.py` (the two anon-client repo functions), `app/repositories/storage.py` (`upload_report_pdf`, its own `StorageError` type since `supabase-py`'s storage client raises a different exception family than `postgrest.exceptions.APIError`).

**Done — frontend.** `frontend/src/lib/publicApi.js` (`publicFetch`) — a SEPARATE fetch helper from `apiFetch`, deliberately never touching `supabase.auth`: this page must work for a visitor with zero Supabase session, not just an unauthenticated one. `VerifyPage.jsx` (`/verify/:certNumber`, routed OUTSIDE `AuthGate`/`AppShell` in `App.jsx` — no nav, no login) shows a loading skeleton, then a green "✓ Valid Certificate" card with the safe fields or a "Certificate not found" card (same for nonexistent and non-issued, matching the backend's own non-distinction), plus a "Report a discrepancy" dialog (required description, optional contact). `SessionLifecyclePanel` gained, once `status === 'issued'`: "Download certificate" (a raw authenticated `fetch` — `apiFetch` only parses JSON, so it can't be reused for a binary PDF — that triggers a normal browser download from the blob) and "View public verification page" (a plain link to `/verify/{certificate_number}`, new tab).

`npm run build` succeeds. Full suite: **596 passed** (was 541 — 16 new `app.services.certificate` unit tests, 5 new `run_rpc_list`/`run_rpc_void` unit tests, 14 new `app.contracts.verify` tests, 12 new `app.routers.verify` router tests, 8 new `/sessions/{id}/report` router tests), `tests/test_purity.py` still green (no engine changes at all this task). Updated `docs/architecture.md` (Database schema: `discrepancy_reports`, the migration-file note; PDF & audit: filled in fully, both parts; API surface: the three new routes, the "every route except /verify" caveat; Frontend: `VerifyPage`, the lifecycle-panel additions; STATUS line), `docs/runbook.md` (the new `PUBLIC_APP_BASE_URL` env var, the `db/migrations/003...` pointer), `.env.example`. Added ADR-0009 (the two `SECURITY DEFINER` exceptions: public verify, and setting `report_storage_path` on an issued session) and `db/migrations/003_pdf_certificate_and_verify.sql` (the exact additive SQL for an already-provisioned live project — table + two functions + grants + policies, idempotent). Did not touch the approval lifecycle, any existing RLS policy, or the schema beyond the one new table and two new functions this task's own scope allowed.

**Next:** Verify on the preview deploy (checklist in the branch reply) — in particular whether the `reports` bucket's own Storage policies actually permit an authenticated user's upload (flagged as unverified above), and that `request.base_url` really does resolve to the right public domain behind Vercel's rewrite (if not, `PUBLIC_APP_BASE_URL` is the escape hatch). The human operator must run `db/migrations/003_pdf_certificate_and_verify.sql` against the live project before this branch is useful there (see the branch reply for the exact SQL). Then: the guided-entry panel and retest flow this task explicitly deferred.

**Open questions:**
- Whether the `reports` bucket needs its own explicit Storage policy added by the human operator for an authenticated upload to succeed — genuinely unverified from this sandbox (no live Supabase egress).
- Whether `request.base_url` resolves correctly behind Vercel's `/api/:path*` rewrite in production — the `PUBLIC_APP_BASE_URL` override exists specifically in case it doesn't.
- No rate-limiting on the public discrepancy-report endpoint (noted above) — a real fix needs durable state, not an in-process counter.
- No existence/issued validation on a discrepancy report's `certificate_number` — deliberate (avoids a leak), but means a report can reference a nonexistent or typo'd number with no feedback to the reporter.
- Whether "who approved" should ever be resolved to a human name (still shown as a shortened UUID) remains open from the previous task, unchanged here.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: SPA fallback so deep links and QR verify URLs resolve

**Done.** Fixed a real production bug: loading any URL directly (not navigating client-side) — `/instruments`, `/sessions/<id>`, and critically `/verify/{certificate_number}` (the exact URL every certificate's QR code encodes) — 404'd from the server. `vercel.json`'s catch-all rewrite forwarded the exact requested path to the frontend service with no fallback (`{"service": "frontend"}`), so it only ever served a real static file (`/`, `/assets/*`, `favicon.svg`); anything else 404'd before React Router ever got a chance to route it client-side. `docs/architecture.md` had actually documented this as "SPA fallback" already in place — it wasn't; that line was wrong.

`vercel.com`/`openapi.vercel.sh` were both still egress-blocked (tried both directly, tried again per this task's instruction). Reasoned from search-engine-summarized third-party/community sources instead (multiple independent, mutually consistent hits): CONFIRMED — a rewrite's `destination` object supports an optional `path` key alongside `service` (`{service, path?}`), specifically for this "route to a service but override the path it receives" case; CONFIRMED — the universally-documented single-project SPA-fallback idiom is exactly this shape minus the service wrapper (`{"source": "/(.*)", "destination": "/index.html"}`), and real static assets are NOT swallowed by it because a real file match takes precedence over a rewrite's destination — this is long-standing, widely-corroborated Vercel routing behavior. INFERRED, not found stated verbatim in a primary source: that this exact "real file wins, rewrite is a fallback" precedence carries over unchanged to the newer multi-service `{service, path}` destination shape specifically. This inference is the one thing only a real deploy proves — flagged explicitly in the branch reply, with the verification steps designed to catch it failing (checking that the actual JS/CSS loaded, not just that some HTML came back, is the specific check that would catch this inference being wrong).

**The fix:** one line. `{"source": "/(.*)", "destination": {"service": "frontend"}}` → `{"source": "/(.*)", "destination": {"service": "frontend", "path": "/index.html"}}`. `/api/:path*`'s own, separate, earlier rule is completely untouched. No app code, engine, backend route, or schema touched — pure routing config, exactly the task's scope.

Updated `docs/architecture.md`'s one-domain-routing section (API surface) to describe the `path` override precisely and correct the previously-wrong "SPA fallback" claim about the old rule. Added the first real entry to `docs/errors/ERROR_LOG.md` (symptom → root cause → fix → prevention) — this is exactly the class of bug that log exists for: real debugging, blocked primary docs, a wrong existing doc claim to catch. `npm run build` succeeds (unaffected — no app code changed). Full pytest suite: unaffected by a JSON routing-config change, re-run anyway to confirm (see branch reply for real output).

**Next:** The real verdict is the next deploy — this cannot be confirmed from this sandbox (no live Vercel deploy access). Verification checklist is in the branch reply: load `/instruments`, `/sessions/<id>`, `/verify/<cert>` directly in a fresh tab (not via in-app navigation) and confirm each renders the app (not a 404) with its real JS/CSS loaded (not just bare HTML — the one thing that would silently fail if the "real file wins over rewrite" inference above turns out wrong for the services shape specifically); confirm `/api/health` still returns JSON, unaffected.

**Open questions:**
- Whether Vercel's `{service, path}` destination override truly preserves "real static file wins over the rewrite" precedence identically to the classic single-project `/index.html` idiom — inferred, not confirmed from a primary source; the next real deploy is the actual test.
- No existence/issued validation on a discrepancy report's `certificate_number` — deliberate (avoids a leak), but means a report can reference a nonexistent or typo'd number with no feedback to the reporter.
- Whether "who approved" should ever be resolved to a human name (still shown as a shortened UUID) remains open from a previous task, unchanged here.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: scope SPA fallback to the frontend service

**Done.** Two prior SPA-fallback attempts and one production outage, both now fully documented in `docs/errors/ERROR_LOG.md`: attempt 1 (root catch-all `{"service": "frontend", "path": "/index.html"}`) shipped but deep links still 404'd; attempt 2 (root catch-all plain string `"/index.html"`) took the ENTIRE site down (including `/`) because there's no `index.html` at the project root in this multi-service layout, and was reverted via `git revert -m 1` (no history rewrite, no force-push). Root `vercel.json` is back to attempt 1's form and this task leaves it exactly as-is.

This task's fix: a new `frontend/vercel.json` (`{"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]}`), scoped to the frontend service's own root where `index.html` genuinely exists after the build.

**Mechanism NOT confirmed from a primary source** — `vercel.com`/`openapi.vercel.sh` still egress-blocked, tried again. Vercel's own `vite-fastapi` reference example (fetched via GitHub raw + README) uses neither a per-service file nor a `path` override, and its demo has no client routes, so it's not a valid precedent either way. Web search turned up two independent real projects that hit and fixed this exact bug — MACantara/Phalanx-Cyber-Academy#465 (merged) and VictorBravo9er/Teacher-Assistant-Workspace#18/#19 — both converged on a DIFFERENT mechanism: nesting `rewrites` directly inside `services.frontend` in the ROOT config, not a separate file. One of those repos' `frontend/vercel.json` was for a standalone (non-services) deploy of that folder, not confirmation of the services-model mechanism this task bets on.

**The one alternative if this fails** (documented in full in ERROR_LOG, since it requires touching the root config, out of this task's scope): delete `frontend/vercel.json`, instead add `"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]` as a property nested inside `services.frontend` in the root `vercel.json` — the mechanism both real-world precedents actually used.

**Also flagged, not acted on:** the root catch-all's `path: "/index.html"` override looks likely inert for this purpose (didn't produce fallback in attempt 1's real deploy, yet real assets kept loading) — recommend dropping it once a working fallback is confirmed, in a follow-up task. Not changed here per the task's explicit "leave root as-is" instruction.

`npm run build` and full pytest suite both unaffected (see branch reply for real output — config/docs-only change, no app code touched).

**Next:** The deploy is the only real verdict. Check order: `/` loads first (would have caught attempt 2's outage immediately — cheapest smoke test, now the standing first check for any SPA-routing change), then `/api/health` returns JSON, then `/instruments` loads styled (real JS/CSS, not bare HTML), then `/verify/<cert>`.

**Open questions:**
- Whether `frontend/vercel.json` is actually read by Vercel under the `services` config model at all — unconfirmed; the documented alternative (nested `services.frontend.rewrites` in the root config) is more strongly evidenced by two independent real-world fixes and should be tried next if this deploy fails.
- Whether the root catch-all's `path` override is truly inert or doing something not yet understood — flagged, not resolved; recommend dropping it once fallback is confirmed working.
- No existence/issued validation on a discrepancy report's `certificate_number` — deliberate (avoids a leak), but means a report can reference a nonexistent or typo'd number with no feedback to the reporter.
- Whether "who approved" should ever be resolved to a human name (still shown as a shortened UUID) remains open from a previous task, unchanged here.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: nest SPA fallback in services.frontend (attempt 4, after attempt 3 also failed on deploy)

**Done.** The user confirmed post-deploy that attempt 3's `frontend/vercel.json` did NOT fix it — `/instruments` still 404'd. That per-service-file mechanism was flagged unconfirmed when it shipped, and evidently Vercel doesn't read it under the `services` config model.

Switched to the mechanism `docs/errors/ERROR_LOG.md`'s previous entry had already identified as better-evidenced: a `rewrites` array nested directly inside `services.frontend` in the ROOT `vercel.json`, plus dropping the root catch-all's `path` override (never confirmed to do anything across three attempts) back to the bare `{"service": "frontend"}` form. Deleted `frontend/vercel.json` — superseded. Full root config now matches, property-for-property, two independent real Vercel Services + Vite projects that hit and fixed this identical bug: MACantara/Phalanx-Cyber-Academy#465 (merged) and VictorBravo9er/Teacher-Assistant-Workspace#18/#19.

Still not confirmed from Vercel's own primary docs (egress-blocked). This is the best-evidenced option found across four attempts, not a certainty — the deploy is still the test. `npm run build` and full pytest suite both re-run and green (config-only change, no app code touched).

**Next:** Deploy and check, in order: `/` loads, `/api/health` returns JSON, `/instruments` loads styled (real JS/CSS), `/verify/<cert>` loads. If this STILL fails, there is no further well-evidenced third-party precedent left to try from this sandbox — the next step would be getting primary Vercel docs access (egress unblocked) or Vercel support directly, not another guess.

**Open questions:**
- Whether this nested-rewrite mechanism actually works under Vercel's `services` model — best real-world evidence available, still unconfirmed from primary docs; if it also fails, escalate rather than guess a fifth shape.
- No existence/issued validation on a discrepancy report's `certificate_number` — deliberate (avoids a leak), but means a report can reference a nonexistent or typo'd number with no feedback to the reporter.
- Whether "who approved" should ever be resolved to a human name (still shown as a shortened UUID) remains open from a previous task, unchanged here.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — feat: role-driven sidebar and dashboard

**Done.** Replaced the top-bar nav with a persistent left sidebar (`AppShell.jsx`) whose items are filtered by role, not disabled — a technician's sidebar has no DOM node for approver-only items at all (`src/lib/navigation.js`, `navItemsForRole`). Responsive: `md`+ keeps the sidebar always visible; below that it's a hamburger-triggered drawer over a backdrop. Bottom of the sidebar is pinned: email, role badge, Log out.

Built a real role-aware dashboard (`DashboardPage.jsx`) to replace the old "getting started" placeholder: technician sees quick actions (Register instrument; Start verification, which links to `/instruments` since a session needs an instrument picked first), three counts, and a "Needs your attention" list of their own draft/returned sessions (returned ones first, with the return reason inline). Approver/admin sees two separated sections — "Awaiting your approval" and "Your own sessions" (captioned with the separation-of-duties rule in plain text, not left mysterious) — plus counts. Empty states are a real dashed-card sentence, not blank space.

**Endpoint gap, worked around, not fixed:** there's no role-scoped `GET /api/sessions`. Built `useAllSessions.js`, which composes it from `GET /api/instruments` + `GET /api/instruments/{id}/sessions` per instrument — correct today because RLS already scopes each per-instrument call right for the caller's role, but `O(instruments)` requests. Flagged in architecture.md as the clean fix for a later backend task.

**Two placeholder pages, not omitted sidebar items:** `DiscrepancyReportsPage.jsx`/`AuditTrailPage.jsx` — chosen over hiding "Discrepancy reports"/"Audit trail" entirely, since omitting them would misrepresent the approver/admin role model. Both say plainly why there's nothing to show: neither `discrepancy_reports` nor `audit_log` has a read endpoint yet (only a public INSERT exists for the former; the latter is write-only from every lifecycle transition). "Users & roles" was omitted outright (not even a placeholder) — no such page exists and it isn't part of this task's role model description either.

One page, `SessionsListPage.jsx` (route `/sessions`), serves both "My sessions" (technician) and "Sessions (all)" (approver/admin) — same `useAllSessions()` data, already RLS-scoped correctly per role; only the title and an extra "Created by" column differ.

`npm run build` succeeds (`2058 modules transformed`, `✓ built in 987ms`); `npm run lint` shows only pre-existing warning patterns already present across every other data-fetching hook/page (no new warning categories introduced). Full pytest suite unaffected — frontend-only task, 596 passed.

**Next:** Verify on the actual preview deploy as both a technician and an approver/admin account — sidebar contents differ correctly, dashboard sections match role, `/sessions`, `/discrepancy-reports`, `/audit-trail` all load, and every pre-existing route (instrument/session/test pages, public `/verify/:cert`) still works inside (or, for `/verify`, outside) the new shell.

**Open questions:**
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Whether this nested-rewrite mechanism actually works under Vercel's `services` model — best real-world evidence available, still unconfirmed from primary docs; if it also fails, escalate rather than guess a fifth shape.
- No existence/issued validation on a discrepancy report's `certificate_number` — deliberate (avoids a leak), but means a report can reference a nonexistent or typo'd number with no feedback to the reporter.
- Whether "who approved" should ever be resolved to a human name (still shown as a shortened UUID) remains open from a previous task, unchanged here.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — feat: guided entry panel for Weighing test

**Done.** Added a keyboard-first guided-entry panel next to the Weighing OIML form table, for the real RRSL workflow: read a value off the machine, record it in one or two keystrokes, without a mouse. The existing click-any-cell table is unchanged in behavior — both surfaces now read/write the exact same cell state via a new shared hook, `useWeighingReadings.js` (extracted from what used to be private state inside `WeighingFormTable`), so a submit from either side is immediately visible on the other.

New files: `src/lib/decimalMath.js` (BigInt-scaled signed string add/multiply — verified against boundary cases like `299.995 + 0.005 = "300"` and `-1.5 + 1.5 = "0"` before trusting it in the UI), `src/components/weighing/formColumns.js` (the ↓/↑-to-up/down mapping, pulled out of `WeighingFormTable.jsx` into its own module so `GuidedEntryPanel` could import it without a circular import), `src/hooks/useWeighingReadings.js` (shared cell state + submit + amendment audit logging), `src/components/weighing/GuidedEntryPanel.jsx` (the panel itself).

**Amend-with-audit:** no backend/schema change was in scope, and there's no `PATCH` endpoint for a reading — but `audit_log`'s own RLS INSERT policy (`actor_id = auth.uid()`) is already open to any authenticated user, not backend-only. So a resubmission whose `I`/`delta_l` actually changed (checked via decimal equality, not string equality — a pure formatting difference never logs a spurious amendment) writes an `audit_log` row directly via the Supabase client, the same per-request JWT-scoped client used everywhere else in the frontend. No backend change, no new gap — just a frontend code path that hadn't used an already-open policy before.

Keyboard flow: Enter commits I → ΔL → submits → advances to the next direction/load, all driven by one flattened list of every `{sequenceNo, apiDirection, field}` stop, shared by auto-advance and explicit Previous/Next buttons. Escape returns focus to the actual table `<input>` the panel is pointing at (a ref map, not just blur). Up/Down arrows nudge ±1g. A `cursor.source: "table"` tag lets a table-cell click update the panel's displayed context without stealing keyboard focus back out of the table. `getCell`/`updateCell` are `useCallback`-memoized specifically so the panel's effects can list them as real dependencies without over-firing on every render — this was the actual fix for an `exhaustive-deps` lint warning my first pass introduced, not a suppression.

`npm run build` succeeds (`2062 modules transformed`, `✓ built in ~900ms-1s` across runs); `npm run lint` shows zero new warning categories versus the pre-existing baseline (confirmed via `git stash -u` against the unmodified branch point). Full pytest suite unaffected — frontend-only task, 596 passed.

**Next:** The real verdict is the preview deploy. Complete an entire Weighing run using only the panel and the keyboard (Tab into the first input, then Enter/arrows/Escape only) — confirm it never needs the mouse. Then click a table cell mid-run to jump the panel there, change a value, and resubmit — confirm the table updates live AND an amendment gets logged (check `audit_log` for `action = 'weighing_reading_amended'`). Confirm the other six tests are completely untouched (still their old per-cell entry, no panel).

**Open questions:**
- The guided-panel pattern (shared readings hook + cursor-driven panel) is Weighing-only for now — extending it to the other six tests is a later task, not attempted here.
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Whether this nested-rewrite mechanism actually works under Vercel's `services` model — best real-world evidence available, still unconfirmed from primary docs; if it also fails, escalate rather than guess a fifth shape.
- No existence/issued validation on a discrepancy report's `certificate_number` — deliberate (avoids a leak), but means a report can reference a nonexistent or typo'd number with no feedback to the reporter.
- Whether "who approved" should ever be resolved to a human name (still shown as a shortened UUID) remains open from a previous task, unchanged here.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: focused layout for test entry screens

**Done.** Production feedback: the Weighing screen didn't work as a workstation — the R76-2 header filled the viewport, the sidebar stole width, the guided panel scrolled away, and the table clipped against the panel. Pure layout fix, applied consistently across all seven test-entry pages, not just Weighing — no computation, submission, or entry behavior changed anywhere.

New `FocusedShell` (`AppShell.jsx`) — a sidebar-free layout, a sibling route to `AppShell` in `App.jsx`, still inside `AuthGate`. All seven test routes (`/sessions/:id/weighing` through `/tilting`) now render inside it instead of `AppShell`; every other authenticated route is unaffected. The sidebar literally doesn't mount on these routes, not just CSS-hidden. `FocusedBackLink` (same file) replaces the plain-text "← Session overview" line all seven pages had, as a small bordered pill — the sole nav affordance left on screen, so it needed to read as prominent, not rebuilt to go anywhere new.

New `CollapsibleFormHeader` (`src/components/oiml/`) — a compact, always-visible, sans-serif summary strip (instrument, e, Max, verification type, date/observer where tracked) above each test's OIML sheet, collapsed by default, with a "Show full form header" toggle revealing the form's own full header block unchanged. All seven `*FormTable.jsx` now take a `verificationType` prop (threaded from each SessionPage's `session.verification_type`, display-only) so the strip can show it.

Weighing-specific (per task scope — only Weighing has the guided panel): the table sheet is now full remaining-column width instead of capped at `max-w-4xl`, so the sticky panel has real room to stay pinned beside a genuinely wide table; the `Load, L` column is `sticky left-0` within the table's own scroll container so it's never lost during horizontal scroll; each table row highlights (light amber) when it matches the guided panel's current `cursor.sequenceNo` — the panel's "Load N of M" text and the highlighted row are now the same fact shown twice.

`npm run build` succeeds (`2063 modules transformed`, `✓ built in ~1s`); `npm run lint` shows zero new warning categories versus the pre-existing baseline. Full pytest suite unaffected — frontend/layout-only task, 596 passed.

**Next:** The real verdict is the preview. Open each of the seven test pages and confirm: no sidebar, full-width table, `FocusedBackLink` returns to the session overview (where the sidebar reappears). On Weighing specifically: header starts collapsed, expands/collapses cleanly; panel stays pinned while scrolling a long load sequence; the active row highlights and tracks the panel as you advance; Load column stays visible on a narrow/scrolled table. Confirm the other six tests' entry, computation, and submission are byte-for-byte unchanged — only their header collapsed.

**Open questions:**
- The active-row highlight and sticky-Load-column treatments are Weighing-only (the only test with the guided panel and the widened table) — whether the other six ever need them depends on whether they get their own guided panels later.
- The guided-panel pattern (shared readings hook + cursor-driven panel) is still Weighing-only — extending it to the other six tests is a later task, not attempted here.
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Whether this nested-rewrite mechanism actually works under Vercel's `services` model — best real-world evidence available, still unconfirmed from primary docs; if it also fails, escalate rather than guess a fifth shape.
- No existence/issued validation on a discrepancy report's `certificate_number` — deliberate (avoids a leak), but means a report can reference a nonexistent or typo'd number with no feedback to the reporter.
- Whether "who approved" should ever be resolved to a human name (still shown as a shortened UUID) remains open from a previous task, unchanged here.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: guided entry follows real loading sequence (up pass, then down pass)

**Done.** Three fixes to the Weighing guided panel — one real domain bug, one precision fix, one responsiveness pass. No computation, submission, or amend-with-audit behavior changed anywhere.

**The domain bug (most important):** the panel walked `load1↓, load1↑, load2↓, load2↑, …` — physically wrong, since that implies adding and removing weights at every single load. OIML R76-1 A.4.4.1: apply loads up to Max, THEN remove them back down. New shared `buildGuidedWalkPositions` (`formColumns.js`, moved out of `GuidedEntryPanel.jsx` so the panel's walk and `WeighingFormTable.jsx`'s reload-resume logic can't drift apart) produces the full increasing pass first (every load ascending), then the full decreasing pass in reverse (every load descending) — for 10 loads, `load1↓…load10↓, load10↑…load1↑`, verified directly with a scratch script before trusting it in the UI. Previous/Next now walk this exact same corrected path. Progress line now says "Increasing pass · Load 5 of 10" / "Decreasing pass · Load 10 of 10" so the technician always knows which physical direction they're in.

**Cell-level highlight:** the row-only highlight was too coarse. `inputCell` now checks the full cursor match (load AND direction AND field) and highlights that one `<td>` strongly (amber + ring), tracking the I→ΔL sub-step. The row keeps a subtler tint for at-a-glance orientation — two levels, not one blunt one.

**Responsiveness — found and fixed three real issues below `lg`:** (1) missing unconditional `min-w-0` on both grid items meant the table's `min-w-[720px]` could force the page wider than the viewport instead of staying inside its own horizontal scroll; (2) the panel stacked below the (potentially long) table, so a tablet user had to scroll past the whole table to reach it — now `order-1` puts it first when stacked; (3) the panel had no width cap below `lg`, stretching edge-to-edge on tablet widths — capped at `max-w-xl`. Also made the "Fine (grams)" button grid responsive (it was hardcoded 6-across; "Scale divisions" already wasn't) and added a drop-shadow to the sticky Load column so it visually reads as pinned rather than glitchy.

`npm run build` succeeds (`2063 modules transformed`, `✓ built in ~1.2s`); `npm run lint` shows zero new warnings in any changed file. Full pytest suite unaffected — frontend-only task, 596 passed.

**Next:** The real verdict is the preview. Complete a full 10-load Weighing run using only the panel and confirm the 20-field order matches exactly: load1↓ through load10↓, then load10↑ back down to load1↑ (40 flat I/ΔL stops total). Confirm Previous walks backward along that same path. Confirm the exact active cell (not just the row) is unmistakable, including across the I→ΔL switch. Resize to tablet and phone widths: confirm no horizontal page overflow, the panel appears above the table when stacked, and it doesn't stretch uncomfortably wide on a tablet.

**Open questions:**
- The active-row highlight and sticky-Load-column treatments are Weighing-only (the only test with the guided panel and the widened table) — whether the other six ever need them depends on whether they get their own guided panels later.
- The guided-panel pattern (shared readings hook + cursor-driven panel) is still Weighing-only — extending it to the other six tests is a later task, not attempted here.
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Whether this nested-rewrite mechanism actually works under Vercel's `services` model — best real-world evidence available, still unconfirmed from primary docs; if it also fails, escalate rather than guess a fifth shape.
- No existence/issued validation on a discrepancy report's `certificate_number` — deliberate (avoids a leak), but means a report can reference a nonexistent or typo'd number with no feedback to the reporter.
- Whether "who approved" should ever be resolved to a human name (still shown as a shortened UUID) remains open from a previous task, unchanged here.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: auto-scale the Weighing test table to fit the viewport

**Done.** "Fit, not fill" — Weighing's 10-column table plus the 320px guided panel could still exceed a real laptop's available CSS-pixel width (OS display scaling, a non-maximized window, dev tools open all shrink it well below 1280px), clipping the table against its own horizontal scroll mid-entry. `WeighingFormTable.jsx` now measures its table wrapper with a `ResizeObserver` and derives a `--tscale` CSS custom property (`clamp(width / 720, 10/12, 1)` — scale-down only, no upscale on a big monitor), which every size-bearing class inside the table (font-size, cell padding, input height) reads via `calc()`. This is dynamic real-CSS-value scaling, not `transform: scale()` — rejected because this table's sticky Load column and the guided panel's DOM-ref-based focus targeting are exactly the two things a scaled ancestor is known to desync. Below the 10/12 readability floor the table stops shrinking (fixed `minWidth: 600px`) and its pre-existing `overflow-x-auto` takes over unchanged. Vertical fit: the same wrapper gained `overflow-y-auto`/`max-h-[65vh]` and the `<thead>` is now `sticky top-0` within it, so a long load sequence scrolls its own rows without losing the header, Passed/Failed, Remarks, or the guided panel out of view — composes cleanly with the pre-existing horizontal `sticky left-0` on the Load column (independent axes, different elements). `GuidedEntryPanel.jsx` was not touched — its ref-based `.focus()` calls keep working unchanged, and the browser's native focus-scroll now conveniently handles scroll-to-active-row for free inside the new internal scroll container. The other six test tables were re-read and confirmed to already fit (no competing side panel; their own `min-w-[…]` is smaller than their sheet's content width) — left unmodified. `docs/architecture.md` Frontend updated in the same commit with the full reasoning (approach chosen and why, the floor, the vertical-fit mechanism). `npm run build` succeeds; `npm run lint` shows zero new warnings; full pytest suite (596 passed) unaffected — frontend-only task.

**Next:** The real verdict is the preview, at a genuinely narrow laptop viewport (try browser zoom 110–125%, or a non-maximized ~1100px window): confirm the whole table (all 10 columns + mpe) and the guided panel are simultaneously visible with no page-level horizontal scroll; confirm text is still comfortably readable at whatever scale it settles to; confirm every input is still clickable/typeable at the right spot, the Load column still pins on horizontal scroll, the active-cell highlight still tracks, and the guided panel's Enter-to-advance still moves focus and scrolls a distant row into view. Also worth trying a session with an unusually long load sequence (if one exists) to see the new internal table scroll + sticky header in action.

**Open questions:**
- The auto-scale mechanism (`useAutoScale`, the `--tscale` custom property pattern) is Weighing-only for now, same as the guided panel it protects — if any of the other six tables ever grows a side panel of its own, the same hook should be reused rather than re-invented.
- No automated visual-regression coverage exists for this — verification here was build/lint/pytest plus reasoning through the DOM/CSS mechanism, not a live browser check (not available in this sandbox); the "verify on preview" list above is the real gate.
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — fix: height-constrained test entry, no page scroll

**Done.** On a real ~720px-tall laptop viewport (the user's actual machine), the test-entry screen still required page scrolling to reach the bottom table rows, Passed/Failed, Remarks, and the guided panel's own buttons — the previous task's `max-h-[65vh]` capped the table, but ~305px of fixed chrome above it (top bar, a full-width back-link pill, a separate 2xl page heading, the collapsed-header summary strip, sheet padding, table header rows) left too little room, and the PAGE itself still scrolled past all of it. Two changes, gated at the same `lg` (1024px) breakpoint the two-column layout already switches on — below `lg`, everything is unchanged (normal page scroll, existing stacking fallback):

1. **Chrome collapsed, across all seven test-entry pages.** New `FocusedPageHeader` (`AppShell.jsx`) merges the back-link pill and page title into one ~30px row, replacing the old back-link-pill-plus-separate-heading pair (~115px); `FocusedBackLink` is deleted (fully absorbed, not left dead). `FocusedShell`'s top bar and `<main>` padding tightened, `CollapsibleFormHeader`'s summary strip tightened, every `*FormTable.jsx`'s workstation sheet padding cut (`p-6 sm:p-8` → `p-2/p-3` + `sm:p-3/p-4`), Passed/Failed and Remarks margins cut (`mt-5` → `mt-3`), Remarks textarea shrunk (`min-h-14/16` → `min-h-10`).
2. **The page container becomes fixed-height and non-scrolling, only at `lg`.** `FocusedShell` gains `lg:h-dvh lg:overflow-hidden`; `<main>` and every `*SessionPage.jsx`'s wrapper become a `flex`/`min-h-0` chain (not `grid` — a grid track stays content-sized even inside an `h-full` grid container, a known gotcha) so each page gets a real, definite height to divide. Weighing gets the full treatment: its two-column layout switches from `grid-cols-[...]` to `lg:flex`, the table's own scroll region (`<thead sticky top-0>`, from the previous task) now sizes to its REAL remaining height instead of a guessed `65vh`, and the guided panel drops `lg:sticky` (nothing to stick against once the page can't scroll) for `lg:h-full lg:overflow-y-auto` — its own content order already puts the input/adjust-buttons/Next before "Last recorded," so a plain top-anchored scroll already keeps the primary controls visible first, no reordering needed. The other six pages get the same fixed frame plus a simpler whole-sheet-scrolls-if-needed fallback (no internal table-row-scroll mechanism was built for them — their content is short enough this rarely engages).

Height budget at 1280×720 (reasoned through — no visual tooling in this sandbox): ~363px of fixed chrome, leaving ~357px for the table's own scrollable rows out of 720px — well past the ~100–150px target. `npm run build` succeeds; `npm run lint` shows only pre-existing warnings, none new; full pytest suite (596 passed) unaffected — frontend-only task. `docs/architecture.md` Frontend updated in the same commit with the full budget breakdown and reasoning.

**Next:** The real verdict is the preview at an actual ~1280×720 window (or browser zoom simulating it): confirm no page-level scrollbar appears at all; confirm the table rows, Passed/Failed, Remarks, and the full guided panel (through its Previous/Next buttons) are all visible without scrolling on a typical load sequence; confirm a longer-than-usual load sequence scrolls ONLY inside the table's own row region, header still pinned; confirm the sticky Load column, active-cell highlight, auto-scale, and guided panel keyboard flow from the last three tasks are all still intact; confirm the other six test pages' chrome is visibly tighter and nothing on them is clipped/unreachable; confirm larger screens (1440p+) show more rows, not a broken layout; confirm below `lg` (tablet/phone width) the page scrolls normally exactly as before this task.

**Open questions:**
- The other six pages got a page-chrome reduction plus a whole-sheet-scroll fallback, not Weighing's precise table-body-only-scrolls treatment — if Repeatability's two 10-row tables or Tilting's three stacked phase tables ever prove too tall for 720px in practice, the same sticky-thead/internal-row-scroll mechanism built for Weighing should be extended to them rather than left as a "scroll the whole form" experience.
- The height budget above is arithmetic reasoning against known Tailwind spacing values, not a measurement from an actual rendered browser (not available in this sandbox) — the "verify on preview" list above is the real gate.
- The auto-scale mechanism (`useAutoScale`, `--tscale`) from the previous task is unchanged and still Weighing-only.
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
- Multi-interval classification/page-6 sub-ranges — known future extensions, unchanged by this task.

---

### [2026-09-27] — feat: session overview as OIML R 76-2 page-9 summary

**Done.** Rebuilt the session overview's test list — previously an ad hoc seven-row app-styled table — as a faithful reproduction of OIML R 76-2's page-9 "Summary of type evaluation" form, the master ~18-clause checklist with Report page / PASSED / FAILED / Remarks columns. Page 9 was read as a rendered image (`pdftoppm`, same method as every other OIML-form component) and reproduced with its exact numbering and row grouping: clause 1's Initial + six °C sub-rows, clause 7's two sub-rows, every a)/b)/c) sub-row under 12.2/12.3/12.4/12.7/13/15, and the "EXAMINATIONS" section header before 16/17 — new `src/lib/summaryChecklist.js` (the row data) and `src/components/session/SessionSummaryTable.jsx` (the rendering).

**Status taxonomy — three states, never conflated.** Implemented + applicable (one of this app's seven checklist tests): the row is a clickable `Link` regardless of not-started/in-progress/complete, with real PASSED/FAILED ticks driven by the exact same `progressByKey`/`computeProgress` shape `SessionPage` already computed — no new status logic, just a different table. N/A (the same instrument-driven `naReason` check `SessionPage`/`AddTestDialog` already use): plain text, the form's own "– –" convention in the data columns, reason in Remarks. Not implemented (every other real page-9 clause — CLAUDE.md scopes this app to the 8.3.3 seven-item checklist): greyed, "—" in the data columns, "Not implemented" in small italic Remarks text — deliberately never worded like "Not started," which is reserved for an implemented test with no data yet, a materially more hopeful claim than "this app has no engine or form for this clause at all."

**One deviation from the printed form, clearly flagged:** page 9 has no line for "Zero/tare device accuracy" (CLAUDE.md groups it under clause 1's A.4.4), but this app tracks it as a separate test/route/form from Weighing. Rather than cram two different verdicts into the form's single "Initial" line or invent a same-looking numbered row the original doesn't have, an extra sub-row is appended under clause 1, visually tinted and labeled "(app addition — not on the printed form)."

**Preserved, integrated around the new table:** the breadcrumb, the instrument/class/status summary card, `SessionLifecyclePanel` (submit/approve/return/issue, certificate number), and `AddTestDialog` — none of their logic changed, only their neighbor in the layout. Still lives in `AppShell` (sidebar visible) — this is a browsing/overview screen, not the sidebar-free entry workstation `FocusedShell` is for. The table itself gets `max-h-[60vh] overflow-y-auto` + `sticky top-0` thead (the same internal-scroll-region pattern the last task established for the Weighing table) so a ~40-row checklist doesn't push the lifecycle panel out of view on a short viewport — a narrower fix than that task's full no-page-scroll treatment, appropriate to a browsing page.

Scope held: no new tests, engines, or endpoints — every un-built clause is a display-only placeholder reading the exact same (unchanged) `PROGRESS_BY_KEY` computation as before. `npm run build` succeeds (`2065 modules transformed`); `npm run lint` shows only the same pre-existing `set-state-in-effect` warnings, nothing new. Full pytest suite (596 passed) unaffected — frontend-only task. `docs/architecture.md` Frontend updated in the same commit.

**Next:** The real verdict is the preview — open a session overview and confirm: all ~18 clauses render in the right order with the right numbering; the seven implemented rows are clickable and open the right test; N/A rows (try a digital instrument for Discrimination, a non-mobile one for Tilting) show "– –" and a reason, not clickable; every other row is visibly greyed and says "Not implemented," not clickable; the appended Zero/tare row under clause 1 is visually distinct from the real form's own lines; the table scrolls internally on a short window without losing the lifecycle panel/breadcrumb; submit/approve/return/issue still all work exactly as before.

**Open questions:**
- The summary table's own bottom "Remarks:" box is local-only, same known gap as every OIML form's header fields (no session-update endpoint yet).
- Whether the six-°C-rows sub-structure under clause 1 will ever need real data (repeated verification at different temperatures) is a full-type-evaluation question CLAUDE.md already scopes out ("Creep and the other full-battery tests are stretch/out-of-scope") — left as permanent not-implemented placeholders, not a near-term gap.
- If any of the eleven not-implemented clauses (2, 3.2, 6.1, 6.2, 7, 9, 10, 11, 12.*, 13, 14, 15, 16, 17) is ever prioritized, its engine/contract/API/form would follow the same pattern the existing seven established — nothing in this task's summary-table work needs to change for that, just flip `placeholder: true` to a real `testKey` in `summaryChecklist.js`.
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-27] — feat: disturbance and voltage-variation test forms

**Done.** Four new test-entry screens beyond the core OIML clause 8.3.3 seven: clause 11 (Voltage variations, A.5.4) and three clause-12.x electrical disturbance tests (12.1 AC mains voltage dips & short interruptions, 12.2 electrical bursts, 12.4 electrostatic discharges). Pages 23/24/25(+26)/29(+30) of R 76-2 were read as rendered images (`pdftoppm`) to match each form's exact table structure; pages 27/32/34/35 (surges, radiated EM, conducted RF, road-vehicle transients) were also read but those four tests were deliberately deferred — see below.

**Two genuinely different shapes.** Voltage variations DOES compute: `app/services/voltage_variations.py` calls `engine.weighing.compute_weighing_result` directly at a fixed 10e load across three power-supply voltage levels (reference/lower/upper) — no new engine, same reuse precedent `zero_tare.py` set. The other three are RECORD-ONLY: OIML's own pass rule for every clause-12.x form is "check if a significant fault occurred" — a physical-bench judgment only a technician with EMC equipment can make, so there is no engine at all (`app/contracts/disturbance.py`'s module docstring has the full reasoning). Their API validates a submitted `condition_key` against that test's own fixed, predefined condition list (`app/services/disturbance.py`) and stores the technician's `indication`/`significant_fault`/`remarks` observation verbatim; `passed = not significant_fault`. All three share ONE router implementation and ONE frontend component (`DisturbanceFormTable.jsx` + `createDisturbanceSessionPage` factory) rather than three near-copies.

**Schema:** `test_type` gained four new enum values (`voltage_variations`, `ac_mains_dips`, `electrical_bursts`, `electrostatic_discharges`) — additive only. `db/migrations/004_disturbance_test_types.sql` has the exact `ALTER TYPE ... ADD VALUE IF NOT EXISTS` statements — **must run against a live project before deploying this branch's backend code**, or the first insert of one of these types fails with a Postgres enum error. `db/schema.sql` updated for a fresh apply.

**Wired end to end:** `testChecklist.js` gained four rows (N/A for non-self-indicating instruments — no electronics to power-vary or disturb); `summaryChecklist.js`'s clause-11/12.1/12.2/12.4 placeholders flipped from "Not implemented" to live, clickable rows on the page-9 summary; `SessionPage.jsx` fetches all four tests' readings and computes their progress via the same `computeProgress` shape every other test already used (fixed totals: 3/7/18/26, never instrument-dependent).

**Prioritized and delivered as directed:** 11, 12.1, 12.2, 12.4 are fully built (contract, service, router with tests, frontend form, wired into both checklists). 12.3 (Surges), 12.5 (Radiated EM immunity), 12.6 (Conducted RF immunity), 12.7 (Road-vehicle transients) are NOT built — no contract, service, route, form, or enum value — and remain "Not implemented" on the summary exactly like every other unbuilt clause. Two documented simplifications: 12.2(b) I/O circuits fixed at 3 generic cable/interface slots (the real form has 9 blank ones); Voltage variations builds one power-supply category/table with one row per level (the real form has two near-identical tables and two blank rows per level).

`npm run build` succeeds (2072 modules). Backend: 35 new tests (contract-level service tests + router tests with the DB layer mocked, same pattern as every other test here), full suite 631 passed (was 596). `docs/architecture.md` updated across four sections (Database schema, Engine design, Contracts, API surface — new "Record-only disturbance tests" subsection — and Frontend) in the same commit.

**Next:** The real verdict is the preview, AFTER running the migration SQL against the live project: open a session, confirm Voltage variations/AC mains dips/Electrical bursts/Electrostatic discharges all appear live (not "Not implemented") on the page-9 summary and are clickable; submit a few readings on each and confirm Passed/Failed responds correctly (a significant-fault tick should flip a disturbance test to Failed; a baseline "without disturbance" row's fault-check should stay inert); confirm a non-self-indicating instrument shows all four as N/A; confirm the other 11 existing tests are completely unaffected.

**Open questions:**
- Surges/Radiated EM/Conducted RF/Road-vehicle transients (12.3/12.5/12.6/12.7) are the clear next slice if this area continues — same pattern, no new architecture needed (a condition list, an enum value migration, a `DisturbanceFormTable` call site).
- 12.2(b)'s 3-fixed-slots simplification may need revisiting if a real verification genuinely has more than 3 I/O interfaces to test — the Remarks field is the documented workaround for now.
- Whether Voltage variations' single-category/single-row-per-level simplification is acceptable to RRSL, or whether the second power-supply-category table needs building, is unconfirmed.
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).

---

### [2026-09-27] — feat: test runs and cross-run comparison

**Done.** Added "runs/conditions" as a first-class concept, so a test can have multiple labelled runs and cross-run comparisons can be computed — infrastructure only, wired into Weighing only. Motivation: clause 1 Weighing (page 9's "Initial" + several °C rows), clause 13 Damp heat (a/b/c: initial → high-temp/85%RH → final), and clause 15 Endurance (a/c: initial → cycle N times → final) are all the SAME procedure re-run under different conditions, where the test IS the comparison between runs — but nothing modeled a "run" before this task. Damp heat and Endurance are NOT built here — still placeholders on the page-9 summary — only the shared infrastructure plus Weighing's own use of it.

**Schema (additive, ADR-0010):** a new `test_runs` table (`run_label`, `conditions` JSONB, server-derived `ordinal`, `unique (session_id, test_type, ordinal)`) — one table across every `test_type`, same hybrid design as `test_readings`/`test_results`. `test_readings.run_id`/`test_results.run_id` are nullable FKs to it. **NULL means "the default/only run"** — the entire backwards-compatibility mechanism: every existing row, and every test that never grows a second run, is completely unaffected, with no backfill and no data migration. `db/schema.sql` updated for a fresh apply; `db/migrations/005_test_runs.sql` has the exact `CREATE TABLE IF NOT EXISTS`/`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`/RLS-policy SQL for a live project — **must run before deploying this branch's backend code** (a submission with a real `run_id` would otherwise hit a missing-column error).

**Engine:** `engine/comparison.py`, `compute_run_comparison` — `variation_error = |Ec_a - Ec_b|`, PASS iff `<= mpe` (limit inclusive). Pure, Decimal-only, order-independent, generic (bare `Ec`/`mpe` Decimals, not a `WeighingResult`) so Damp heat/Endurance can reuse it unmodified. 14 new tests (`tests/test_comparison.py`): boundary cases (exactly at mpe from both sides), sign handling (opposite-signed Ec, both-negative Ec, order of the two runs never changing the verdict), zero-mpe exact-agreement, and negative-mpe/non-Decimal rejection.

**Backend:** `app/contracts/runs.py`/`app/repositories/runs.py`/`app/services/runs.py` are generic across `test_type` (for Damp heat/Endurance to reuse later); only `app/routers/sessions.py`'s Weighing section is wired to them. New: `GET/POST /sessions/{id}/weighing/runs` (list/create — `POST` 409s if not draft, `ordinal` always server-derived), `GET /sessions/{id}/weighing/runs/compare?run_id_a=&run_id_b=` (per-load variation error, matching by `(sequence_no, direction)`, either id omittable = the default run). `WeighingReadingSubmitIn`/`WeighingReadingRecordOut` gained an optional `run_id` (omitted/null = default run, unchanged behavior); `POST .../weighing/readings` 422s if a given `run_id` doesn't belong to this session's Weighing test. `GET .../weighing/readings` gained an optional `?run_id=` query param (omitted = the default run, the exact pre-existing query). 18 new backend tests (services + router, DB mocked, same pattern as every prior test file) — run creation/ordinal assignment, run-scoped submission, the unknown/foreign-session `run_id` 422 cases, default-run listing, explicit-run filtering, and the compare endpoint.

**Frontend (Weighing only):** `RunSelector.jsx` — near-invisible with zero explicit runs (just a small "+ Add another run" affordance); becomes a small tab bar ("Initial" + each created run's label) plus an inline create form (label + optional temperature) once a technician adds one. `WeighingSessionPage` fetches runs alongside session/instrument/sequence, re-fetches readings keyed by the selected run, and fetches the comparison (selected run vs. Initial) once a non-default run is selected. `WeighingFormTable` is mounted `key={selectedRunId ?? "default"}` so switching runs remounts the table (and `useWeighingReadings`, which only ever seeds its cell state once) from that run's own fetched readings, rather than adding resync logic to the hook. A per-load comparison table (`|ΔEc|` vs mpe, PASS/FAIL) renders below Passed/Failed once 2+ runs exist. Guided panel, auto-scale, and the height-constrained layout are all untouched — they operate on whatever state the currently-mounted per-run table instance hands them.

`npm run build` succeeds (2073 modules). Full suite: 662 passed (was 631) — 14 new engine tests + 18 new backend tests, zero regressions. `docs/architecture.md` updated (Database schema, a new "Runs, conditions, and cross-run comparison" subsection, Engine design, Contracts, API surface, Frontend) plus ADR-0010, in the same commit.

**Next:** The real verdict is the preview, AFTER running `005_test_runs.sql` against the live project: open a Weighing session with no runs yet and confirm it looks and behaves exactly as before (no tab bar, no extra chrome); click "+ Add another run," create one labelled "at 40 °C," confirm a tab bar appears with "Initial" and the new run, and that switching tabs shows a genuinely separate, empty set of readings for the new run (not the Initial run's data); submit a few readings on the new run and confirm the comparison table appears below Passed/Failed showing sensible `|ΔEc|` values against Initial's own readings at matching loads; confirm every other existing test (Zero-tare, Repeatability, Eccentricity, Discrimination, Tilting, Sensitivity, Voltage variations, the three disturbance tests) is completely unaffected.

**Open questions:**
- Damp heat (clause 13) and Endurance (clause 15) are the clear next consumers of this infrastructure — same pattern (a `test_type`-parameterized route section calling the already-generic `app/services/runs.py`, plus each test's own change-point engine module), no new schema/architecture needed.
- Whether "Initial" should ever become a real `test_runs` row (rather than a frontend-only convention for `run_id = null`) is deliberately left open — ADR-0010 explains why NULL-as-default doesn't foreclose that later.
- The comparison UI currently compares the selected run only against Initial (not against every other run pairwise) — sufficient for clause 1's a-vs-b shape; Damp heat's three-way a/b/c comparison may want a richer view when it's built.
- `GET /api/sessions` (role-scoped) is the clean fix for `useAllSessions.js`'s O(instruments) composition — backend work for a later task.
- Read endpoints for `discrepancy_reports` (admin-only per CLAUDE.md) and `audit_log` don't exist yet — both sidebar items are placeholders until they do.
- Band-1 intermediate load spacing and the 10e start-load convention are still documented placeholders pending RRSL confirmation, unchanged by this task.
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
