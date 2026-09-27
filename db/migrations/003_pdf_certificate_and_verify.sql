-- Migration 003 — PDF certificate generation + public verification.
--
-- ADDITIVE ONLY: one new table (discrepancy_reports) and two new
-- SECURITY DEFINER functions (set_report_storage_path,
-- get_public_certificate_info) — no existing table, column, or RLS
-- policy is touched or rewritten. Safe to run against a live project with
-- existing data. See docs/decisions/0009 for why these two functions
-- exist and why get_public_certificate_info() is the one deliberate
-- anonymous-read exception in this schema.
--
-- Apply via the Supabase SQL editor or
-- `psql <connection> -f db/migrations/003_pdf_certificate_and_verify.sql`.
-- Idempotent: re-running it is a no-op (IF NOT EXISTS / OR REPLACE /
-- DROP POLICY IF EXISTS throughout).

create table if not exists discrepancy_reports (
  id uuid primary key default gen_random_uuid(),
  certificate_number text not null,
  description text not null,
  contact text,
  created_at timestamptz not null default now()
);

alter table discrepancy_reports enable row level security;

drop policy if exists discrepancy_insert_anon on discrepancy_reports;
create policy discrepancy_insert_anon on discrepancy_reports for insert
  with check (true);

drop policy if exists discrepancy_select_admin on discrepancy_reports;
create policy discrepancy_select_admin on discrepancy_reports for select
  using (public.get_my_role() = 'admin');

CREATE OR REPLACE FUNCTION public.set_report_storage_path(p_session_id uuid, p_path text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  v_created_by uuid;
  v_status session_status;
BEGIN
  SELECT created_by, status INTO v_created_by, v_status
  FROM test_sessions WHERE id = p_session_id;

  IF v_created_by IS NULL THEN
    RAISE EXCEPTION 'session not found' USING ERRCODE = 'P0002';
  END IF;

  IF v_status <> 'issued' THEN
    RAISE EXCEPTION 'insufficient_privilege: report_storage_path may only be set on an issued session'
      USING ERRCODE = '42501';
  END IF;

  IF NOT (auth.uid() = v_created_by OR public.get_my_role() IN ('approver', 'admin')) THEN
    RAISE EXCEPTION 'insufficient_privilege: only the session''s creator, an approver, or an admin may set this'
      USING ERRCODE = '42501';
  END IF;

  UPDATE test_sessions SET report_storage_path = p_path WHERE id = p_session_id;
END;
$function$;

GRANT EXECUTE ON FUNCTION public.set_report_storage_path(uuid, text) TO authenticated;

CREATE OR REPLACE FUNCTION public.get_public_certificate_info(p_certificate_number text)
 RETURNS TABLE (
   certificate_number text,
   status session_status,
   instrument_model text,
   instrument_manufacturer text,
   instrument_type_designation text,
   accuracy_class accuracy_class,
   verification_type verification_type,
   issued_at timestamptz
 )
 LANGUAGE sql
 STABLE SECURITY DEFINER
AS $function$
  SELECT
    s.certificate_number,
    s.status,
    i.model,
    i.manufacturer,
    i.type_designation,
    i.accuracy_class,
    s.verification_type,
    s.issued_at
  FROM test_sessions s
  JOIN instruments i ON i.id = s.instrument_id
  WHERE s.certificate_number = p_certificate_number
    AND s.status = 'issued';
$function$;

GRANT EXECUTE ON FUNCTION public.get_public_certificate_info(text) TO anon, authenticated;
