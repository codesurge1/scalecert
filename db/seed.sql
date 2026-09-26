-- Seed: role promotion for the demo accounts (ADR-0004: seed-script-only, no admin UI).
-- PREREQUISITE: first create two accounts via Supabase Auth (app sign-up or Auth dashboard):
-- a technician and an approver. handle_new_user() makes BOTH 'technician' on sign-up.
-- Then run this over a privileged connection (SQL editor / service role) so it bypasses RLS.
-- Adjust the emails to your actual demo accounts.

update public.profiles p
set role = 'approver', full_name = 'Demo Approver'
from auth.users u
where u.id = p.id and u.email = 'approver@scalecert.demo';

update public.profiles p
set full_name = 'Demo Technician'
from auth.users u
where u.id = p.id and u.email = 'technician@scalecert.demo';

-- Optional admin:
-- update public.profiles p set role = 'admin', full_name = 'Demo Admin'
-- from auth.users u where u.id = p.id and u.email = 'admin@scalecert.demo';
