# 0002 — New Supabase project

## Status

Accepted

## Context

The existing Supabase project holds the old Node/TS 4-test prototype's schema and RLS policies. The rebuild is a schema rework (6 test_type values, new tables, an audit `data` column), handed to new devs, and needs reproducibility. RLS fails silently, so stale policies from the old model are a landmine.

## Decision

Use a new Supabase project. Port only validated assets: the `get_my_role` and `handle_new_user` functions verbatim, and re-author RLS patterns and the adversarial `42501` test against the new schema. Do not delete the old project — keep it (paused if needed for the free-tier cap) as a reference and as the fallback demo. The database is defined entirely by a checked-in migration, never by dashboard clicks.

## Consequences

Clean slate, no stale policies, deterministic resets; small setup cost; the old prototype remains a working safety net.
