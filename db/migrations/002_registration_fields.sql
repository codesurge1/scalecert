-- Migration 002 — R 76-2 page-6 "General information concerning the type"
-- registration fields.
--
-- ADDITIVE ONLY: every column is nullable, no existing column is touched,
-- no data is rewritten. Safe to run against a live project with existing
-- `instruments` rows — none of them are affected; the new columns simply
-- come back NULL until a row is edited. See docs/decisions/0007 for why
-- this migration exists as a standalone file alongside db/schema.sql
-- (which remains the single source of truth for a FRESH apply — this file
-- is the exception, for an already-provisioned project that must not be
-- reset).
--
-- Apply via the Supabase SQL editor or `psql <connection> -f
-- db/migrations/002_registration_fields.sql`. Idempotent: re-running it is
-- a no-op (every ADD COLUMN is IF NOT EXISTS).

alter table instruments
  add column if not exists applicant text,
  add column if not exists instrument_category text,
  add column if not exists u_nom numeric,
  add column if not exists u_min numeric,
  add column if not exists u_max numeric,
  add column if not exists mains_frequency numeric,
  add column if not exists battery_u_nom numeric,
  add column if not exists printer_status text,
  add column if not exists zero_device_type text,
  add column if not exists tare_device_type text,
  add column if not exists initial_zero_setting_range_pct numeric,
  add column if not exists temperature_range_min numeric,
  add column if not exists temperature_range_max numeric,
  add column if not exists load_cell_manufacturer text,
  add column if not exists load_cell_type text,
  add column if not exists load_cell_capacity numeric,
  add column if not exists load_cell_number text,
  add column if not exists load_cell_class_symbol text,
  add column if not exists software_version text,
  add column if not exists identification_no text,
  add column if not exists interfaces text;
