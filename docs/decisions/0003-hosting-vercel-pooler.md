# 0003 — Hosting on Vercel with the Supabase pooler

## Status

Accepted

## Context

FastAPI-on-serverless has known footguns: Postgres connection exhaustion, cold starts. A container host would avoid them, but the team is committed to Vercel.

## Decision

Host both builds on Vercel via Vercel Services (one domain). Because of serverless, database access must use the Supabase connection pooler (Supavisor, transaction mode), never the direct connection. Accept the cold-start tradeoff on the public verify path. Certificate format is `SC-{YEAR}-{6-digit sequential}`.

## Consequences

Simple single-platform deploy; pooler is mandatory; watch cold-start latency on the demo's QR→verify path.
