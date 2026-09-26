-- ScaleCert schema — the single source of truth for the database (ADR-0005).
-- Apply to a FRESH Supabase project via the SQL editor or `psql < db/schema.sql`.
-- Written to run once against a clean database. The database is defined ONLY here,
-- never by dashboard clicks (ADR-0002).

create extension if not exists pgcrypto;

-- ============ ENUMS ============
create type user_role as enum ('technician', 'approver', 'admin');
create type accuracy_class as enum ('I', 'II', 'III', 'IIII');
create type verification_type as enum ('initial', 'subsequent', 'in_service');
create type session_status as enum ('draft', 'submitted', 'returned', 'approved', 'issued', 'superseded');
create type indication_type as enum ('digital', 'analog', 'non_self_indicating');
create type test_type as enum (
  'weighing',        -- A.4.4-A.4.6 indication errors (incl. zero/tare device accuracy variant)
  'repeatability',   -- A.4.10
  'eccentricity',    -- A.4.7, 3.1 (weights)
  'discrimination',  -- A.4.8  (gated: N/A for digital instruments)
  'tilting',         -- A.5.1.3 (gated: mobile instruments only)
  'sensitivity'      -- A.4.9  (gated: non-self-indicating instruments only)
);

-- ============ CORE TABLES ============
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role user_role not null default 'technician',
  full_name text,
  created_at timestamptz not null default now()
);

create table instruments (
  id uuid primary key default gen_random_uuid(),
  registered_by uuid not null references profiles(id),
  application_no text,
  type_designation text,
  manufacturer text,
  model text,
  serial_number text,
  accuracy_class accuracy_class not null,
  e_value numeric not null,        -- verification scale interval e, in grams
  d_value numeric,                 -- actual scale interval d, if distinct from e.
                                   -- "Resolution during test" on the report form = COALESCE(d_value, e_value).
  max_capacity numeric not null,   -- Max, grams
  min_capacity numeric,            -- Min, grams (nullable: only required if >= 100mg)
  indication_type indication_type not null,
  is_mobile boolean not null default false,
  is_multi_interval boolean not null default false,
  -- R 76-2 page-6 "General information concerning the type" report-form
  -- fields (docs/decisions/0007), added alongside the identity/e/Max/Min/
  -- indication_type/accuracy_class fields above — all nullable, so a
  -- technician can fill the core (identity + e/Max/Min) and leave the rest.
  applicant text,
  instrument_category text,
  -- Power supply.
  u_nom numeric,              -- rated mains voltage, V
  u_min numeric,              -- minimum mains voltage, V
  u_max numeric,              -- maximum mains voltage, V
  mains_frequency numeric,    -- Hz
  battery_u_nom numeric,      -- rated battery voltage, V
  printer_status text,        -- 'built_in' | 'connected' | 'not_present' | 'no_connection'
                               -- (validated at the Pydantic layer, not here — same pattern as
                               -- session_test_selection.zero_device_status).
  zero_device_type text,      -- 'non_automatic' | 'semi_automatic' | 'automatic_zero_setting'
                               -- | 'initial_zero_setting' | 'zero_tracking'
  tare_device_type text,      -- 'tare_balancing' | 'tare_weighing' | 'preset_tare_device'
                               -- | 'subtractive_tare' | 'additive_tare' | 'combined_zero_tare_device'
  initial_zero_setting_range_pct numeric,  -- % of Max
  temperature_range_min numeric,           -- deg C (form's "T = -")
  temperature_range_max numeric,           -- deg C (form's "T = +")
  -- Load cell.
  load_cell_manufacturer text,
  load_cell_type text,
  load_cell_capacity numeric,
  load_cell_number text,
  load_cell_class_symbol text,
  software_version text,
  identification_no text,
  interfaces text,            -- number and nature, free text
  created_at timestamptz not null default now()
);

create table test_sessions (
  id uuid primary key default gen_random_uuid(),
  instrument_id uuid not null references instruments(id),
  verification_type verification_type not null,
  status session_status not null default 'draft',
  created_by uuid not null references profiles(id),
  approved_by uuid references profiles(id),
  certificate_number text unique,          -- assigned at approval only: SC-{YEAR}-{6-digit seq}
  supersedes_session_id uuid references test_sessions(id),
  report_storage_path text,                -- Supabase Storage key, set once the PDF is generated
  -- Patches from the RRSL visit (Part D.3): report header/context fields.
  observer_name text,
  test_date date,
  environmental_conditions jsonb,          -- start/max/end x Temp/Rel.h/Time/Bar.pres
  remarks text,
  created_at timestamptz not null default now(),
  submitted_at timestamptz,
  approved_at timestamptz,
  issued_at timestamptz
);

create table session_test_selection (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references test_sessions(id) on delete cascade,
  test_type test_type not null,
  applicable boolean not null default true,
  na_reason text,
  zero_device_status text,   -- Patch: per-test zero-setting/zero-tracking device status.
                             -- Allowed value set varies by test_type; validated at the Pydantic layer, not here.
  status text not null default 'pending',   -- pending / in_progress / complete
  unique (session_id, test_type)
);

create table test_readings (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references test_sessions(id) on delete cascade,
  test_type test_type not null,
  sequence_no integer not null,
  direction text,        -- 'up' | 'down' | null  (bidirectional tests use this)
  series_no integer,     -- Repeatability's two series; null for other tests
  position_no integer,   -- Eccentricity's 1-4; null for other tests
  data jsonb not null,   -- raw inputs (L, I, deltaL, ...); shape enforced by a Pydantic model per test_type
  entered_by uuid not null references profiles(id),
  created_at timestamptz not null default now()
);

create table test_results (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references test_sessions(id) on delete cascade,
  test_type test_type not null,
  reading_id uuid references test_readings(id),   -- null for a test-level (not per-reading) verdict
  result jsonb not null,   -- full derivation: E, Ec, E0, mpe, margin, ... per test_type
  passed boolean,
  computed_at timestamptz not null default now()
);

-- Append-only audit log. MINIMAL for now (ADR-0005): the `data` column is present;
-- hash-chain columns (prev_hash / this_hash) are deferred to a later change if the
-- chain is built (stretch scope). `data` already captures the exact action payload.
create table audit_log (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references test_sessions(id),
  actor_id uuid references profiles(id),
  action text not null,
  data jsonb,
  created_at timestamptz not null default now()
);

create sequence certificate_number_seq;

-- ============ FUNCTIONS (ported verbatim from the validated original build) ============
CREATE OR REPLACE FUNCTION public.get_my_role()
 RETURNS user_role
 LANGUAGE sql
 STABLE SECURITY DEFINER
AS $function$
  SELECT role FROM profiles WHERE id = auth.uid();
$function$;

CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  INSERT INTO public.profiles (id, role) VALUES (NEW.id, 'technician');
  RETURN NEW;
END;
$function$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============ ROW LEVEL SECURITY ============
alter table profiles enable row level security;
alter table instruments enable row level security;
alter table test_sessions enable row level security;
alter table session_test_selection enable row level security;
alter table test_readings enable row level security;
alter table test_results enable row level security;
alter table audit_log enable row level security;

-- profiles: read own (privileged roles read all); only admin changes roles.
create policy profiles_select_own on profiles for select
  using (id = auth.uid() or public.get_my_role() in ('approver','admin'));
create policy profiles_update_admin on profiles for update
  using (public.get_my_role() = 'admin') with check (public.get_my_role() = 'admin');
-- INSERT is done by handle_new_user() (SECURITY DEFINER). Role promotion is done by the
-- seed script over a privileged connection (ADR-0004), which bypasses RLS.

-- instruments: any authenticated user reads; owner registers/edits.
create policy instruments_select_auth on instruments for select
  using (auth.uid() is not null);
create policy instruments_insert_own on instruments for insert
  with check (registered_by = auth.uid());
create policy instruments_update_own on instruments for update
  using (registered_by = auth.uid() or public.get_my_role() = 'admin')
  with check (registered_by = auth.uid() or public.get_my_role() = 'admin');

-- test_sessions: creator sees own; approver/admin see all.
create policy sessions_select on test_sessions for select
  using (created_by = auth.uid() or public.get_my_role() in ('approver','admin'));
create policy sessions_insert_own on test_sessions for insert
  with check (created_by = auth.uid());
-- Technician edits own session while draft/returned and may move it to submitted,
-- but WITH CHECK forbids a resulting status of approved/issued (that is the approver's move).
create policy sessions_update_owner on test_sessions for update
  using (created_by = auth.uid() and status in ('draft','returned'))
  with check (created_by = auth.uid() and status in ('draft','submitted'));
-- Approver/admin act on OTHERS' sessions (separation of duties): created_by <> auth.uid()
-- is the core rule. A technician approving their OWN session matches no policy -> 42501.
create policy sessions_update_approver on test_sessions for update
  using (public.get_my_role() in ('approver','admin')
         and created_by <> auth.uid()
         and status in ('submitted','returned','approved'))
  with check (public.get_my_role() in ('approver','admin')
              and created_by <> auth.uid());
-- NOTE: finer transition validity (no backwards moves; issue/supersede rules) is enforced
-- at the API layer as defense in depth. RLS here is the coarse separation-of-duties guard.
-- 'issued' rows match no UPDATE policy and are therefore immutable at the DB.

-- session_test_selection: creator manages while draft; creator + approver/admin read.
create policy sts_select on session_test_selection for select
  using (exists (select 1 from test_sessions s where s.id = session_id
         and (s.created_by = auth.uid() or public.get_my_role() in ('approver','admin'))));
create policy sts_write on session_test_selection for all
  using (exists (select 1 from test_sessions s where s.id = session_id
         and s.created_by = auth.uid() and s.status = 'draft'))
  with check (exists (select 1 from test_sessions s where s.id = session_id
         and s.created_by = auth.uid() and s.status = 'draft'));

-- test_readings: creator writes while draft; creator + approver/admin read.
create policy readings_select on test_readings for select
  using (exists (select 1 from test_sessions s where s.id = session_id
         and (s.created_by = auth.uid() or public.get_my_role() in ('approver','admin'))));
create policy readings_write on test_readings for all
  using (entered_by = auth.uid() and exists (select 1 from test_sessions s where s.id = session_id
         and s.created_by = auth.uid() and s.status = 'draft'))
  with check (entered_by = auth.uid() and exists (select 1 from test_sessions s where s.id = session_id
         and s.created_by = auth.uid() and s.status = 'draft'));

-- test_results: same visibility/writability as readings (written server-side alongside them).
create policy results_select on test_results for select
  using (exists (select 1 from test_sessions s where s.id = session_id
         and (s.created_by = auth.uid() or public.get_my_role() in ('approver','admin'))));
create policy results_write on test_results for all
  using (exists (select 1 from test_sessions s where s.id = session_id
         and s.created_by = auth.uid() and s.status = 'draft'))
  with check (exists (select 1 from test_sessions s where s.id = session_id
         and s.created_by = auth.uid() and s.status = 'draft'));

-- audit_log: INSERT-only + scoped SELECT. NO update/delete policies at all -> append-only at the DB.
create policy audit_insert on audit_log for insert
  with check (actor_id = auth.uid());
create policy audit_select on audit_log for select
  using (public.get_my_role() = 'admin'
         or (session_id is not null and exists (select 1 from test_sessions s where s.id = session_id
             and (s.created_by = auth.uid() or public.get_my_role() = 'approver'))));
