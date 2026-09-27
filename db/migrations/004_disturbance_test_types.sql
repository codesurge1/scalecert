-- Migration 004 — clause 11 and clause 12.x test_type enum values
-- (feat/disturbance-test-forms).
--
-- ADDITIVE ONLY: five new values on the existing `test_type` enum, nothing
-- else. No existing table, column, RLS policy, or enum value is touched.
-- Safe to run against a live project with existing data — a new enum value
-- can never conflict with a row that already exists (nothing could have
-- used it before this migration ran).
--
-- Apply via the Supabase SQL editor or
-- `psql <connection> -f db/migrations/004_disturbance_test_types.sql`,
-- BEFORE deploying the backend code from this task (the new
-- /voltage-variations, /ac-mains-dips, /electrical-bursts, and
-- /electrostatic-discharges endpoints will fail their first insert with a
-- Postgres "invalid input value for enum test_type" error otherwise).
--
-- Idempotent: `ADD VALUE IF NOT EXISTS` (Postgres 12+) makes re-running
-- this a no-op.
--
-- NOTE ON TRANSACTIONS: unlike ordinary DDL, `ALTER TYPE ... ADD VALUE`
-- cannot run in the same transaction block as a later statement that uses
-- the new value — but each statement below is its own standalone
-- transaction (the default outside an explicit BEGIN/COMMIT), so running
-- this whole file straight through (psql or the Supabase SQL editor) is
-- fine as-is. Do not wrap these five statements in a manual BEGIN/COMMIT.

ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'voltage_variations';
ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'ac_mains_dips';
ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'electrical_bursts';
ALTER TYPE test_type ADD VALUE IF NOT EXISTS 'electrostatic_discharges';
