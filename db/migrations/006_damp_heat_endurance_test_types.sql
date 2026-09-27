-- Migration 006: damp_heat + endurance test_type values (feat/damp-heat-endurance).
-- Purely additive against an already-provisioned (live) project — see
-- docs/decisions/0007 for why this accompanies, rather than replaces, the
-- db/schema.sql edit (which is authoritative for a FRESH apply).
--
-- Two `ALTER TYPE ... ADD VALUE` statements, each its own statement (same
-- convention as 004_disturbance_test_types.sql): Postgres does not allow a
-- newly-added enum value to be used in the SAME transaction that added it,
-- so if the SQL editor wraps this whole file in one transaction, run these
-- two statements SEPARATELY (one at a time) rather than as one paste.
--
-- Run this against the live project before deploying this task's backend
-- code, or the first insert of a 'damp_heat'/'endurance' test_readings row
-- fails with a Postgres enum error.

ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'damp_heat';

ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'endurance';
