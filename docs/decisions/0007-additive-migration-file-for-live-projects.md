# 0007 — An additive `db/migrations/` file may accompany a `schema.sql` change, for live projects only

## Status

Accepted

## Context

ADR-0005 chose a single checked-in `db/schema.sql`, applied to a fresh project and reset (drop + re-apply) whenever it changes — explicitly *not* a series of migration files, to keep the workflow to "one file, one apply, one reset." That's the right default when there's no real data yet to lose.

This task (instrument registration rebuilt as the OIML R 76-2 page-6 form) adds 21 new nullable `instruments` columns. A demo/pilot project may already have real registered instruments and sessions in it by the time this ships; forcing "drop and re-apply the whole schema" to add columns that don't touch any existing data is a disproportionate, avoidable reset.

## Decision

`db/schema.sql` remains the single source of truth for a **fresh** apply — ADR-0005 is not reversed. For a change that is purely additive (new nullable columns, no rewrite of existing columns or data, no destructive statement), a standalone file under `db/migrations/` (sequentially numbered, e.g. `002_registration_fields.sql`) may accompany the same `schema.sql` edit in the same commit, containing just the `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` statements needed to bring an *already-provisioned* project up to date without a reset. Both files must describe the identical end state — `schema.sql` is still what a fresh project gets, the migration file is only how an existing one catches up.

This is a narrow exception, not a reversal: it applies only when every statement in the migration file is additive and idempotent (`IF NOT EXISTS`, nullable columns, no data loss possible by construction). A change that renames, drops, or rewrites a column, or that needs a data backfill, still means "edit `schema.sql`, reset the project" per ADR-0005 — this ADR does not authorize a general migration-file workflow for that case.

## Consequences

- Existing live data survives a nullable-column addition without a reset — the actual problem this ADR solves.
- Two files must be kept in sync by hand for an additive change (`schema.sql`'s inline `create table` and the migration's `ALTER TABLE`) — a manual-consistency cost ADR-0005 explicitly avoided; acceptable here because the migration file is small, reviewed in the same commit, and the two are trivially diffable against each other.
- Still no general migration-ordering system, no down-migrations, no migration runner — this is one narrowly-scoped file for one additive change, not new tooling. The next non-additive schema change goes back to ADR-0005's reset workflow.
- The human operator must still run the migration by hand against the live project (this repo has no CI/CD pipeline that applies it automatically) — same manual-apply model ADR-0002/0005 already established for `schema.sql` itself.
