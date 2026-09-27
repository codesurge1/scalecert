# 0010 — Runs/conditions as a first-class concept: a `test_runs` table, and nullable `run_id` (not a backfill) for backwards compatibility

## Status

Accepted

## Context

Several OIML type-evaluation tests are structurally the SAME procedure re-run more than once, where the test IS the comparison between runs, not just a repetition:

- **Clause 1, Weighing** (R76-2 page 9) — the report form has an "Initial" row plus several "at N °C" rows: the same Weighing load sequence, re-run at different ambient temperatures.
- **Clause 13, Damp heat** (a/b/c) — initial test (at reference temperature) → high temperature + 85% RH → final test (back at reference temperature). The pass criterion compares the initial and final corrected errors.
- **Clause 15, Endurance** (a/c) — initial test → cycle the instrument N times → final test. `durability error = |Ec_initial − Ec_final|`, checked against mpe.

Nothing in the schema before this task modeled "a run" at all. `test_readings`/`test_results` are keyed by `session_id` + `test_type` (+ discriminators like `direction`/`series_no`/`position_no`), with no way to say "this reading belongs to the SECOND time this test was run, under THESE conditions." Building Damp heat or Endurance without first solving this would mean inventing a run concept ad hoc, once, for whichever of the two got built first — and Weighing's own multi-temperature rows (already on the page-9 summary as placeholders) would still have nowhere to record a second run either.

This task (`feat/test-runs-conditions`) is scoped to the infrastructure and to wiring it into Weighing ONLY — Damp heat and Endurance remain unbuilt (still placeholders on the summary), by explicit instruction. The infrastructure has to be usable by both of them later without modification.

## Decision

**A new `test_runs` table** (`id`, `session_id`, `test_type`, `run_label`, `conditions` JSONB, `ordinal`, `created_by`, `created_at`), one table across every `test_type` — the same "hybrid design" `test_readings`/`test_results` already use, rather than a per-test runs table. `conditions` is free-form JSONB (temperature, humidity, cycle count, ...) — opaque to the database, validated (if at all) at the Pydantic contract layer, matching this schema's existing "shape enforced above the DB, not inside it" convention for `data`/`result`. `ordinal` (`unique (session_id, test_type, ordinal)`) is always server-derived — one past however many runs already exist for that session+test_type — never client-supplied, the same "server derives it, nothing downstream trusts a client-invented value" discipline the Weighing load sequence's `L` already established.

**`test_readings.run_id`/`test_results.run_id` are nullable FKs to `test_runs`, and NULL means "the default/only run" — a valid, permanent state, not a placeholder awaiting backfill.** This was the one genuinely load-bearing choice in this task. The alternative — giving every test's first/implicit run a real `test_runs` row, created automatically alongside the session or on first reading — was rejected: it would require either (a) backfilling a `test_runs` row for every existing session's every test_type that has ever recorded a reading (a real data migration against a live project, for a feature only one test currently uses), or (b) leaving old rows with no run reference while new rows always have one, which is a *worse* inconsistency than NULL, since it would need a second rule ("no run_id AND no matching migration" vs "no run_id, period") to explain the same fact. NULL-as-default avoids both: every reading/result row ever written, and every reading of a test that never grows beyond its one run (every test in this app except Weighing, today), is simply and permanently correct with `run_id = null` — no migration required, no distinction between "old" and "new" rows, and no `test_runs` row is ever required to exist for a test's first/only run.

**Cross-run comparison lives in the engine as its own pure function** (`engine/comparison.py`, `compute_run_comparison`), not folded into `compute_weighing_result` or duplicated per consuming test. It takes two bare `Ec`/`mpe` `Decimal`s — not a `WeighingResult` — specifically so Damp heat's and Endurance's own change-point math (which will also produce an `Ec`/`mpe` pair, per R76-1's own construction of both tests) can call it unmodified, without needing to go through Weighing's own result type at all.

**Only Weighing's router is wired to any of this in this task.** `app/contracts/runs.py` / `app/repositories/runs.py` / `app/services/runs.py` are already generic over `test_type` — nothing about them is Weighing-specific — but `app/routers/sessions.py` only adds `GET/POST .../weighing/runs`, an optional `run_id` on the two existing Weighing readings routes, and `GET .../weighing/runs/compare`. Wiring Damp heat or Endurance later means adding their own routes that call the same repository/service functions with `test_type='damp_heat'`/`'endurance'` — no schema change, no new engine function, no new repository/service function.

## Consequences

- Every existing test (Zero-tare, Repeatability, Eccentricity, Discrimination, Tilting, Sensitivity, Voltage variations, the three record-only disturbance tests) is completely unaffected: none of their contracts, services, or routes were touched, and their `test_readings`/`test_results` rows simply carry `run_id = null` like every row does that predates this migration.
- A future "give every implicit run a real row" migration remains possible if ever needed (e.g. if a UI wants to show "Initial" as a genuine `test_runs` row instead of a frontend-only convention) — it would be a new, separate, additive decision, not something this ADR forecloses; nothing here assumes NULL can never be backfilled, only that it doesn't NEED to be for this task's scope.
- `test_runs` has no RLS policy of its own beyond the standard creator/approver-or-admin visibility + creator+draft writability shape (`runs_select`/`runs_write`, `db/schema.sql`) — deliberately the same shape as `session_test_selection`'s `sts_select`/`sts_write`, not `test_readings`' `entered_by`-scoped `readings_write`, since a run is session-level metadata (who labelled it), not a per-actor reading.
- `db/migrations/005_test_runs.sql` is purely additive (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) and requires no backfill step, no data migration, and no downtime — consistent with every migration file before it (ADR-0007).
