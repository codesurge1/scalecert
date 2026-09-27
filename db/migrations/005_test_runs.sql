-- Migration 005: runs/conditions (feat/test-runs-conditions).
-- Purely additive against an already-provisioned (live) project — see
-- docs/decisions/0007 for why this accompanies, rather than replaces, the
-- db/schema.sql edit (which is authoritative for a FRESH apply).
--
-- Adds a `test_runs` table (a labelled run of a test under a given set of
-- conditions) and nullable `run_id` FKs on `test_readings`/`test_results`.
-- NULL run_id means "the default/only run" — every existing reading/result
-- row, and every test that never grows a second run, is completely
-- unaffected: no backfill, no data migration, nothing to reconcile.
--
-- Run this against the live project (SQL editor or `psql`) before
-- deploying this task's backend code, exactly like 002/003/004 before it.

create table if not exists test_runs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references test_sessions(id) on delete cascade,
  test_type test_type not null,
  run_label text not null,
  conditions jsonb,
  ordinal integer not null,
  created_by uuid not null references profiles(id),
  created_at timestamptz not null default now(),
  unique (session_id, test_type, ordinal)
);

alter table test_readings add column if not exists run_id uuid references test_runs(id);
alter table test_results add column if not exists run_id uuid references test_runs(id);

alter table test_runs enable row level security;

drop policy if exists runs_select on test_runs;
create policy runs_select on test_runs for select
  using (exists (select 1 from test_sessions s where s.id = session_id
         and (s.created_by = auth.uid() or public.get_my_role() in ('approver','admin'))));

drop policy if exists runs_write on test_runs;
create policy runs_write on test_runs for all
  using (exists (select 1 from test_sessions s where s.id = session_id
         and s.created_by = auth.uid() and s.status = 'draft'))
  with check (exists (select 1 from test_sessions s where s.id = session_id
         and s.created_by = auth.uid() and s.status = 'draft'));
