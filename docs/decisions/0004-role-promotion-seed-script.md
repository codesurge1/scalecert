# 0004 — Role promotion is seed-script-only

## Status

Accepted

## Context

`handle_new_user()` defaults every signup to `technician`. Separation of duties can't be demoed without an approver account, and there is no admin UI to promote one.

## Decision

Role promotion is seed-script-only for this build: `db/seed.sql` promotes the demo approver account to `approver` over a privileged connection (bypassing RLS). No admin UI is built for role management unless Phase 3 finishes early.

## Consequences

Resolves the open question cheaply for the demo. Promoting real users later is a manual `UPDATE` (or a future admin-UI task) rather than a self-service flow.
