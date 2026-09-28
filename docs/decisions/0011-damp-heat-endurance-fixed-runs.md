# 0011 — Damp heat/Endurance as FIXED, auto-provisioned runs (not technician-labelled ones); Endurance's cycling step lives in a run's own conditions

## Status

Accepted

## Context

`feat/test-runs-conditions` (ADR-0010) built the runs/conditions infrastructure — a `test_runs` table, nullable `run_id` on `test_readings`/`test_results` (NULL = the default/only run), and a pure cross-run comparison engine function — but wired it into Weighing ONLY, and deliberately left Damp heat (clause 13) and Endurance (clause 15) unbuilt. Both are now in scope for this task, and both are exactly the "same procedure re-run under different conditions" shape ADR-0010 already named as the motivating case:

- Damp heat (R76-2 pages 37-39): three runs — a) Initial test (reference temperature), b) test at high temperature + 85% RH, c) Final test (reference temperature). Each is a full Weighing table; each has its own `|Ec| <= mpe` check.
- Endurance (R76-2 pages 46-47): two Weighing-table runs — a) Initial, c) Final — around a non-computed "b) Performance of the test" cycling step (number of loadings, load applied), plus the form's own extra column: durability error due to wear and tear = `|Ec_initial - Ec_final|`, which must be `<= mpe` for EVERY load.

Two design questions this task had to answer that ADR-0010 left open (because Weighing's own runs are optional and technician-labelled, a genuinely different shape):

1. **How does a Damp heat/Endurance session get its runs?** Weighing's runs are created one at a time, by the technician, with a free-text label, only if they ever re-run the test under a different condition — the implicit default (`run_id = null`) covers every session that doesn't. Damp heat and Endurance have no such default: the run structure (a/b/c, a/c) IS the test. Every reading of either test needs a real `run_id` from the start.
2. **Where does Endurance's cycling step (loadings/load applied) live?** It's not a reading (no `I`/`ΔL`/direction), not a full run (no Weighing math), and CLAUDE.md's guardrail against unnecessary schema growth argues against a bespoke column pair on `test_runs` or a new table just for two fields used by exactly one test.

## Decision

**Damp heat/Endurance get FIXED, auto-provisioned runs, not technician-created ones.** Each test's service module (`app/services/damp_heat.py`, `app/services/endurance.py`) declares its own `FIXED_RUN_LABELS` (three for Damp heat, two for Endurance — the exact R76-2 sub-heading text, e.g. `"a) Initial test (at reference temperature)"`). A new `POST /sessions/{id}/{test}/setup` endpoint, idempotent, creates whichever of a test's fixed labels don't already exist for this session (`app.services.runs.ensure_fixed_run_labels`, the one genuinely new function `feat/test-runs-conditions`' generic `app/services/runs.py` needed) and returns the full, ordered list — safe to call on every page load, a no-op once all of a test's runs already exist. Every reading submitted to either test carries a real `run_id` (the contract field stays `Optional[str]` for shape parity with Weighing's own, but is always populated in practice) — there is no implicit default run for either test, unlike every other test in this app.

**Endurance's cycling step is recorded as `conditions` JSONB on the Final run, not a new table or columns.** A dedicated, validated endpoint — `PATCH /sessions/{id}/endurance/cycling` (`EnduranceCyclingIn`: `number_of_loadings: Optional[int]`, `load_applied: Optional[StrictDecimal]`) — looks up the Final run by its own fixed label server-side (never a client-supplied run id, same "server derives it" discipline as every computed/derived value in this app) and writes the payload into that run's `conditions` column (`app.repositories.runs.update_run_conditions`, new — the only place `test_runs` gets an UPDATE at all). This keeps `test_runs.conditions` doing exactly the job ADR-0010 already gave it (per-run condition metadata, opaque to the DB) rather than growing the schema for two fields one test uses.

**Endurance's durability verdict is computed on demand, not stored.** `GET /sessions/{id}/endurance/durability` looks up the Initial/Final runs by their fixed labels, builds both runs' reading records, and calls the existing `app.services.runs.compare_records` + the new `engine.comparison.compute_durability_check` (an aggregate: every load's variation error must be `<= mpe`, not just some — mirroring `compute_repeatability_series`'s spread check and `compute_tilting_loaded_check`'s max-deviation check, the established "whole-set property" pattern in this engine). Nothing about the verdict is persisted — it is always a function of the currently-stored Initial/Final readings, same "recompute, don't cache a derived aggregate" precedent `app/services/repeatability.py`/`app/services/tilting.py` already set.

**Both tests reuse `WeighingFormTable`/`RunSelector` verbatim, via two small generic additions rather than new form components:** `useWeighingReadings`/`WeighingFormTable` gained an `apiPath` prop (default `"weighing"`) deciding which test's readings endpoint a submission posts to; `RunSelector` gained `showDefaultTab`/treats `onCreateRun` as optional, so its tab bar can represent a fixed run set with no implicit default and no "add run" affordance. Every existing caller (Weighing) is unaffected — both new props/behaviors default to the pre-existing shape.

## Consequences

- Weighing's own runs/comparison code, tests, and behavior are completely untouched — every addition here is either a new file (contract/service/router-section per test) or an additive, default-preserving prop on shared components.
- A future test with this same "fixed, known-in-advance run structure" shape (none currently planned) reuses `ensure_fixed_run_labels`/the `POST .../setup` pattern/`apiPath` directly — no new infrastructure decision needed.
- `EnduranceCyclingIn`'s fields are validated (unlike Weighing's own free-form `conditions: Optional[dict]` on run creation, which stays opaque JSON) because they are genuinely structured input with a known shape, not arbitrary condition metadata — a deliberately different discipline for the same JSONB column, justified by what's actually being written into it each time, not a blanket rule either way.
- `db/migrations/006_damp_heat_endurance_test_types.sql` is purely additive (two `ALTER TYPE ... ADD VALUE IF NOT EXISTS` statements, each its own statement per Postgres's same-transaction restriction — ADR-0007/004's precedent) and requires no backfill.
