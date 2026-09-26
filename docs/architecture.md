# Architecture

Purpose: describe the system's structure — schema, engine, roles, API surface — as the single source of truth for how ScaleCert is built.

> STATUS: schema, roles, session lifecycle (as of ADR-0005), engine design (Weighing calculation + load-sequence generator), the Weighing contracts/API-validation layer, and the API surface (instruments/sessions/Weighing readings — DB-integration verified via preview only, not in-sandbox) are authoritative. PDF and audit are pending their build tasks.

## System overview

## Scope (the 7 tests)

## Tech stack

## Database schema

`db/schema.sql` is the single source of truth for the database (ADR-0002, ADR-0005) — never dashboard clicks.

Seven tables:
- **profiles** — one row per `auth.users` row, holds `role` (technician/approver/admin) and `full_name`. Created by `handle_new_user()` on signup.
- **instruments** — the registered NAWI: accuracy class, `e_value`/`d_value`, Max/Min capacity, indication type, and the `is_mobile`/`is_multi_interval` flags that gate the conditional tests.
- **test_sessions** — one verification session per instrument visit: status, certificate number, approval trail, and the report-header patch fields (see below).
- **session_test_selection** — which of the six `test_type`s apply to this session, with an NA reason where they don't and a per-test `zero_device_status`.
- **test_readings** — raw technician input per test, one row per reading (or per series/position where applicable), keyed by `test_type`.
- **test_results** — computed verdicts derived from readings, keyed by `test_type` and optionally `reading_id`.
- **audit_log** — append-only record of actions taken against a session.

Enums: `user_role`, `accuracy_class`, `verification_type`, `session_status`, `indication_type`, `test_type`.

**Hybrid design.** `test_readings` and `test_results` are each a single table across all six `test_type`s, not one table per test. Test-type-specific fields live in a `data` / `result` JSONB column; the shape of that JSON is enforced by a Pydantic model per `test_type` at the API layer, not by the database. This keeps the schema stable as test-specific fields evolve, at the cost of the DB not being able to validate that shape itself.

**Report-header patches.** Four fields were added to `test_sessions` from the RRSL visit (Part D.3): `observer_name`, `test_date`, `environmental_conditions` (start/max/end × Temp/Rel.h/Time/Bar.pres, JSONB), and `remarks`. A fifth patch, `zero_device_status`, lives on `session_test_selection` instead, since it's per-test rather than per-session.

**Resolution during test.** The report form's "resolution during test" field is not its own column — it renders as `COALESCE(d_value, e_value)` from `instruments`.

**Certificate numbering.** `certificate_number` on `test_sessions` is assigned only at approval time, formatted `SC-{YEAR}-{6-digit sequential}` drawn from `certificate_number_seq` — never before approval (see CLAUDE.md guardrails).

## Engine design

The `engine/` package (repo root, sibling to `backend/` and `frontend/`) is pure: standard library only, no FastAPI, Supabase, network, DB, or wall-clock imports — enforced mechanically by `tests/test_purity.py`, which walks every `engine/*.py` file's AST and fails if any top-level import resolves outside `sys.stdlib_module_names`.

All arithmetic uses `Decimal`, never `float` — a boundary verdict (e.g. `Ec == mpe` exactly) must not turn on binary floating-point rounding. Every function requires all of its inputs explicitly (no default values); a missing or wrong-typed input raises `TypeError`/`ValueError` rather than being guessed (`tests/test_input_validation.py` proves this for both the MPE lookup and the Weighing calculation).

**MPE lookup** (`engine/mpe.py`, `lookup_mpe`) — inputs: `accuracy_class`, `m` (load in multiples of `e`), `e` (for the grams conversion), `verification_type`. Looks up R76-1 Table 6 by class and `m`-band (upper bound inclusive, next band's lower bound exclusive of it); `initial`/`subsequent` return the table value as-is, `in_service` doubles it. Returns an `MpeResult` carrying not just the number but the band boundaries used (`band_lower_m`, `band_upper_m`) and the class/type/e/m it was computed from — so a result is traceable back to which row of Table 6 produced it, not just the resulting figure.

**Weighing calculation** (`engine/weighing.py`, `compute_weighing_result`) — `E = I + 1/2*e - deltaL - L`, `Ec = E - E0`, verdict `PASS` iff `|Ec| <= mpe` (limit inclusive). Returns a `WeighingResult` with the full derivation (`L, I, delta_l, E0, E, Ec, mpe, margin, passed`) plus the `MpeResult` that produced `mpe` — never just a boolean. `margin = mpe - |Ec|` so a near-miss is visible, not just a verdict.

**Validation.** The canonical worked example (Class III, e=1g, initial, load 300g → Band 1 → mpe=±0.5g; reading 300.4g → PASS; 300.6g → FAIL — `docs/plan.md` Phase 1) was written as a failing test *before* the engine existed, then implemented until green. Per CLAUDE.md, one example is a smoke test, not validation: no verdict is trusted until `tests/test_mpe_boundaries.py`'s boundary-value table passes — every Table 6 band edge from both sides for all four classes, the at-limit-inclusive/just-over verdict boundary in both directions, `in_service` doubling actually flipping a verdict, and the Max/Min ends of each class's table range.

**Load-sequence generator** (`engine/load_sequence.py`, `generate_load_sequence`) — produces the applied-load (`L`) sequence for a Weighing test, so the technician enters only Indication (I) and additional load (ΔL); `L` is never technician-entered. Inputs: `accuracy_class`, `e`, `max_capacity`, `min_capacity` (the sole genuinely optional argument — `Optional[Decimal]`, not a default), `verification_type`.

- **Verification count is ≥5, not ≥10.** The 8.3.3 verification checklist this project implements needs ≥5 distinct test loads (`MIN_VERIFICATION_LOAD_COUNT`); the "≥10" figure seen in some visit-report material is for full type evaluation — a separate, out-of-scope test battery. Conflating the two would overtest every verification for no regulatory reason.
- **Sourced anchors** (always present when applicable): Max; Min, but only if given and ≥100 mg (0.1 g, per A.4.4.1 — otherwise omitted, never clamped or guessed); every Table 6 band-transition load that falls within `[Min-or-0, Max]`. The transition loads are read directly out of `engine.mpe.BAND_TABLE` — the same table `lookup_mpe` uses — never a second hardcoded copy of the band edges.
- **Band-1 fill spacing is a documented placeholder, not a sourced value.** OIML does not prescribe how many extra loads, or where, to place inside Band 1 beyond the mandatory anchors, and RRSL has not yet confirmed a convention (`docs/plan.md` Open questions). When anchors fall short of the ≥5 minimum, the gap is filled with evenly spaced points strictly inside Band 1 — deterministic and reproducible (never random, so a certification record reproduces identically), but explicitly labeled (`FILL_SPACING_STRATEGY`) as a convention pending RRSL confirmation, changeable in one place. Every `LoadEntry.kind` is `max` / `min` / `band_transition` (sourced) or `fill` (convention) — `LoadEntry.is_anchor` is `False` only for `fill` — so a report or UI can never present a placeholder point as a mandated one.
- **Bidirectional testing is not dropped, just deferred.** The plan requires each load tested going up and coming back down; this generator returns only the distinct ascending `L` values — expanding each into an "up" and "down" reading is the reading layer's job (Phase 2), not this module's.
- **Single-interval only, for now.** The generator assumes a single-interval instrument (one `e` across the whole range). Multi-interval instruments (`instruments.is_multi_interval`) — where `e` itself changes across sub-ranges — are a known future extension, not handled here.

## Contracts / API validation layer

`backend/app/contracts/` holds the Pydantic v2 models that sit between the wire and the engine — one module per `test_type`. Only `weighing.py` exists so far (the vertical slice); the other six test types get their own module later, following its shape.

**Decimal-as-string discipline (the critical rule).** Every numeric field uses a shared `StrictDecimal` type (`backend/app/contracts/common.py`): it accepts a JSON string (preferred) or an int, and **rejects a bare float outright** — not because pydantic's own default `Decimal` coercion is unsafe (checked: it converts a float via `str()` internally, so `300.6` doesn't silently become `300.5999...`), but because the contract layer's job is to guarantee this regardless of that implementation detail, and to keep API clients on the wire-safe path (quoted decimal strings) rather than relying on an unquoted JSON number happening to work out. On output, `model_dump(mode="json")` serializes every `Decimal` field back to a string via a `PlainSerializer` — a `Decimal` never crosses the wire as a JSON number in either direction.

**One source of truth for enums.** `WeighingReadingIn`/`WeighingResultOut` use `engine.types.AccuracyClass` and `VerificationType` directly as field types — not a mirrored copy. An API value and an engine value are the same Python object, so they cannot drift; `test_contract_enums_are_the_engine_enums_not_a_copy` locks this in. `Direction` (up/down) has no engine equivalent — the engine is direction-agnostic — so it's defined once in `common.py`.

**The engine↔contract seam is two named functions**, not scattered conversion code: `reading_to_engine_kwargs(reading: WeighingReadingIn) -> dict` (feeds `engine.weighing.compute_weighing_result`) and `result_to_out(result: WeighingResult) -> WeighingResultOut` (the reverse). `WeighingResultOut` mirrors the engine's full derivation (`L, I, delta_l, E0, E, Ec, mpe, margin, passed`) plus the MPE band context (`mpe_in_e`, `band_lower_m`, `band_upper_m`) — never just a boolean.

**`L` is a validated field, not a trusted one.** `WeighingReadingIn.L` exists on the model (system-generated from `engine.load_sequence`, per its own field description) precisely so it passes through the same validation as every other value — the contract's job is to validate shape, not to decide provenance.

The engine package remains completely untouched by this layer: `backend/app/contracts/` imports from `engine/`, never the reverse, and `tests/test_purity.py` (run in the same suite as these contract tests) confirms no Pydantic import ever leaks into `engine/`.

**Known follow-up, not solved here.** The `engine/` package lives at the repo root, outside `backend/`, which is the Vercel Services `backend` service's own root directory. Wiring these contracts into real routes will need to confirm `engine/` is actually reachable in that service's deployed bundle — a deployment detail for the task that does that wiring, not this one.

## Roles & permissions

Three roles: `technician`, `approver`, `admin`. New signups default to `technician` via `handle_new_user()`; promotion to `approver`/`admin` is seed-script-only (ADR-0004), not an admin UI.

The non-negotiable rule is separation of duties: no one both produces and approves the same result. This is enforced twice:
- **At the database**, via RLS: the `sessions_update_approver` policy requires `created_by <> auth.uid()` in addition to the approver/admin role. A technician attempting to approve their own session matches no UPDATE policy at all and the write fails with Postgres error `42501`.
- **At the API layer**, as defense in depth, independent of the RLS check.

## Session lifecycle

`draft → submitted → approved → issued`, with two additional states:
- **returned** — an approver sends a submitted session back; the technician edits it from `draft` or `returned` and resubmits.
- **superseded** — an issued report later found to be wrong is never edited in place. A new session is created referencing the original via `supersedes_session_id`; the original session remains retrievable, not deleted.

`issued` sessions are immutable at the database: no UPDATE policy on `test_sessions` matches a row once its status is `issued`, so no role (including admin, under the current policy set) can modify it through RLS.

## API surface

The FastAPI app is mounted entirely under `/api` (an `APIRouter(prefix="/api")` in `backend/app/main.py`), so route handler code and public URL match exactly — no prefix-stripping happens at the routing layer.

Deployed as two [Vercel Services](https://vercel.com/docs/services) in one project on one domain (`/vercel.json` at the repo root): `frontend` (the Vite build, `framework: "vite"`, served at `/`) and `backend` (the FastAPI app, `entrypoint: "main:app"` — a thin shim at `backend/main.py` re-exporting the real `app` from `backend/app/main.py`, following the entrypoint convention Vercel expects at the service root). A rewrite sends `/api/:path*` to the backend service; everything else falls back to the frontend service, which serves `index.html` (SPA fallback).

Locally, the same mount path is used: `uvicorn app.main:app` still serves `/api/health`, `/api/whoami`, `/api/whoami/debug` on `http://localhost:8000`. CORS is same-origin (and therefore off) in production; for local dev, an env-configurable allowed origin (`CORS_ALLOW_ORIGIN`, default `http://localhost:5173`) replaces what would otherwise be a permissive wildcard.

Current routes:
- `GET /api/health` — liveness, no auth, no DB.
- `GET /api/whoami` / `GET /api/whoami/debug` — the walking-skeleton RLS debug routes.
- `POST /api/instruments`, `GET /api/instruments`, `GET /api/instruments/{id}` — register/list/fetch an instrument.
- `POST /api/sessions`, `GET /api/sessions/{id}` — open a Weighing session for an instrument (also inserts its `session_test_selection` row for `weighing`); fetch a session including its selected tests.
- `GET /api/sessions/{id}/weighing/sequence` — the generated load sequence (see below).
- `POST /api/sessions/{id}/weighing/readings` — submit one reading; the server computes the verdict and writes reading + result together.

Every route depends on `app.deps.get_auth_context` (`Depends(get_auth_context)`) — one reusable dependency that extracts the caller's JWT, builds the per-request user-scoped client (`app.supabase_client.user_client`), and resolves `auth.uid()` via GoTrue's `get_user(jwt)` so a route needing it for an insert payload (`registered_by`, `created_by`, `entered_by`, `actor_id`) never has to re-derive it. There is still no service-role client anywhere in `backend/`.

**Server-derives-L.** The technician never enters or sees a raw `L` value as something they typed — `GET .../weighing/sequence` calls `engine.load_sequence.generate_load_sequence` with the session's instrument params and returns each entry's `sequence_no` (its stable index), `L`, `m`, `kind`, and `mpe`. `POST .../weighing/readings` takes only `sequence_no`, `I`, `delta_l`, `direction`, `E0` from the client (`WeighingReadingSubmitIn` — deliberately narrower than the engine-ready `WeighingReadingIn`), regenerates the *same* sequence server-side, and looks up `L` for that `sequence_no`. Both routes call `app.services.weighing.build_sequence` — the one place `generate_load_sequence` is invoked from the API layer — so they can never disagree about what a given `sequence_no` means. Deterministic, so nothing about the sequence is stored; it's recomputed on every call.

**Reading + result, written together.** supabase-py/PostgREST has no client-side multi-table transaction. The chosen approach: insert the reading, then insert the result; if the result insert fails, delete the just-inserted reading rather than leave one with no computed verdict (`app/routers/sessions.py`, `submit_weighing_reading`). A single Postgres RPC doing both inserts atomically would remove this rollback step entirely — a reasonable follow-up, not built in this task.

**Readings only while `draft`** (`app.services.sessions.ensure_session_is_draft`) — a 409 otherwise. This deliberately only enforces that one rule; the `returned → draft` reopening and the `submitted`/`approved`/`issued` transitions are a later task's concern, and nothing here blocks building that later.

**Audit is non-fatal.** On reading submission, an `audit_log` row is inserted (`action='weighing_reading_submitted'`); if that insert fails, a warning is logged and the request still returns success (docs/plan.md: "audit writes non-fatal but surfaced"). No hash chain (stretch/out of scope, ADR-0005).

**Two Decimal policies, deliberately different, at two different boundaries.** `StrictDecimal` (`app.contracts.common`) governs untrusted CLIENT input and rejects a bare float outright. Supabase/PostgREST returns `numeric` columns as JSON numbers (Python `float`) on every read — a completely different, trusted boundary — so `app.db_decimal.decimal_from_db_value` converts those via `Decimal(str(value))` (safe: Python's float repr is shortest-round-trip) before a DB row ever reaches an `Out` contract's `StrictDecimal` field. Passing a raw DB-row float straight into a `StrictDecimal` field would incorrectly trip the client-input rejection on every normal read — `instrument_out_from_row`/`instrument_params_from_row` (`app.contracts.instrument`) exist specifically to do this conversion first.

**Errors are typed, not raw 500s:** missing/invalid body → 422 (Pydantic, automatic); session not `draft` when submitting a reading → 409; `sequence_no` out of range → 422; instrument/session not found *or* not visible under RLS → 404 (deliberately not distinguished — CLAUDE.md: RLS fails silently, and a caller shouldn't be able to probe for the existence of another user's row either way).

**Known follow-up, not solved here.** `engine/` lives outside `backend/`'s own Vercel-service root (flagged when the Weighing contracts were added) — these routes now actually call `engine.load_sequence`/`engine.weighing` at request time, so this needs resolving before a real deploy, not just before a real route existed.

**Testing note.** This sandbox has no egress to a live Supabase project. The pure logic — contract validation, the engine↔contract adapters, the `sequence_no → L` lookup, the not-draft rule — is unit-tested directly (`backend/tests/services/`, `backend/tests/contracts/`). The routes themselves are tested with the entire DB layer mocked (`backend/tests/routers/`) via `app.dependency_overrides` (for auth) and `monkeypatch` (for `app.repositories.*`) — this proves the routing/error-code/orchestration logic, not that the real SQL against the real schema behaves as expected. That needs the preview deploy (see SESSION_LOG.md for the verification steps).

## PDF & audit

## Out of scope

- Audit hash-chain columns (prev_hash/this_hash) are deferred (ADR-0005); the `data` column is present now, and the chain is stretch scope.
