# 0005 — Schema as a single checked-in file; audit hash-chain deferred

## Status

Accepted

## Context

We need a checked-in DB definition (ADR-0002) and chose simplicity over migration tooling; the audit hash chain is stretch scope.

## Decision

The schema is one checked-in `db/schema.sql` (not a series of CLI migration files), applied to a fresh project and reset by re-running it. `audit_log` ships minimal for now — a `data` JSONB column and append-only RLS (no UPDATE/DELETE policies) — with hash-chain columns (`prev_hash`/`this_hash`) deferred to a later edit of `schema.sql` if the chain is built.

## Consequences

Simplest possible workflow and reproducibility: one file, one apply, one reset. The tradeoff is no automatic version-ordering of schema changes, and one later schema edit plus a reset if/when the hash chain is added.
