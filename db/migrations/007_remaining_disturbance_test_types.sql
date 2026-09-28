-- Migration 007: the last four record-only test_type values (clauses
-- 12.3/12.5/12.6/12.7), completing 12.1-12.7 (feat/remaining-disturbance-forms).
-- Purely additive against an already-provisioned (live) project — see
-- docs/decisions/0007 for why this accompanies, rather than replaces, the
-- db/schema.sql edit (which is authoritative for a FRESH apply).
--
-- Four ALTER TYPE ... ADD VALUE statements, each its own statement (same
-- convention as 004/006): Postgres does not allow a newly-added enum value
-- to be used in the SAME transaction that added it, so if the SQL editor
-- wraps this whole file in one transaction, run these four statements
-- ONE AT A TIME rather than as one paste.
--
-- Run this against the live project before deploying this task's backend
-- code, or the first insert of one of these four test_types fails with a
-- Postgres enum error.

ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'surges';

ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'radiated_em_immunity';

ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'conducted_rf_immunity';

ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'road_vehicle_transients';
