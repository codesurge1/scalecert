# CLAUDE.md — ScaleCert

ScaleCert digitizes OIML R76 verification/certification for Non-Automatic Weighing Instruments (NAWIs) at India's RRSLs. This file is the router and the rulebook. It is read every session — keep it lean (rules and pointers, never inlined knowledge). When this file and the code disagree, the code is correct: fix this file.

## When to read what

| If you are working on… | Read first |
|---|---|
| Anything (every session) | this file, then SESSION_LOG.md (last 2–3 entries) |
| Schema, data model, API contracts, engine design | /docs/architecture.md |
| Build sequence, phases, scope, priorities | /docs/plan.md |
| Writing or running tests | /docs/testing.md |
| Local setup, deploy, env, DB reset | /docs/runbook.md |
| Why a past choice was made | /docs/decisions/ (ADRs) |
| A bug that resembles a past one | /docs/errors/ERROR_LOG.md |

## Non-negotiable guardrails

- Scope is the OIML clause 8.3.3 seven-item verification checklist: Weighing (incl. zero/tare device accuracy), Repeatability, Eccentricity (3.1 weights), Discrimination, Tilting, Sensitivity. Creep and the other full-battery tests are stretch/out-of-scope — do not build them unless explicitly told.
- Auth: never use the Supabase service-role key for user-scoped data access. Every request that reads/writes a user's data uses a per-request, user-scoped client built from the caller's JWT, so Row Level Security applies as that user. Service-role is for privileged system tasks only.
- RLS fails silently — a misauthored policy returns zero rows, not an error. Handle both failure shapes (explicit error vs. empty result) and keep a "who am I / what can I see" debug path.
- The calculation engine is pure: no FastAPI, Supabase, network, DB, or wall-clock imports inside the engine package. Enforce with an import check in CI.
- Never trust the engine on a single example. No calculated verdict is trusted until the boundary-value test table passes (every MPE band edge from both sides, Max, Min, both directions, initial and in-service-doubled).
- Database access uses the connection pooler (Supavisor, transaction mode), never the direct connection — required on serverless.
- Generated PDFs go to Supabase Storage, never local disk (serverless filesystem is ephemeral).
- Certificate format is SC-{YEAR}-{6-digit sequential}, assigned at approval time via a Postgres sequence — never before approval.
- Weighing load sequence is auto-generated; the technician enters only Indication (I) and additional load (ΔL), never the applied load L.
- Secrets never enter git. .env* is gitignored; only .env.example (blank values) is committed.
- Separation of duties: no one both produces and approves the same result. Enforce at the database (RLS) AND the API layer (defense in depth).

## Documentation Maintenance Protocol (MANDATORY — these files are living, not write-once)

These rules are part of the Definition of Done. A task is not complete until the docs it affects are updated in the same commit as the code.

- Code-wins rule. If code and a doc conflict, the code is the source of truth — update the doc in the same commit. Never leave a doc knowingly stale.
- Architecture changes. Any change to schema, data model, API surface, or engine contracts MUST update /docs/architecture.md in the same commit. A commit that changes these without touching architecture.md is invalid.
- Decisions. Any non-trivial or hard-to-reverse choice gets a new numbered ADR in /docs/decisions/ (see 0001). ADRs are append-only: never rewrite a past ADR; supersede it with a new one that references it.
- Errors. Any bug that took real debugging gets an entry appended to /docs/errors/ERROR_LOG.md (symptom → root cause → fix → prevention). This is how the next cold session avoids re-solving it.
- Session log. At the end of every working session, append an entry to SESSION_LOG.md (what changed, what's next, any new open questions). At the start of every session, read the last 2–3 entries.
- Keep this file lean. Do not inline architecture, plans, or knowledge here — link to /docs. If a rule needs more than a couple of lines of explanation, it belongs in a /docs file that this table points to.

## Pre-commit checklist (run before every commit)

- [ ] Docs affected by this change are updated in this same commit (see Maintenance Protocol).
- [ ] New decision? → ADR added. Debugged a real bug? → ERROR_LOG updated.
- [ ] No secret, key, or .env file is staged.
- [ ] No guardrail above is violated.
- [ ] SESSION_LOG.md updated if this ends a session.

## Branch-per-task workflow
- Every task is done on a branch off `main`. Never commit directly to `main`.
- Branch names: `feat/…`, `fix/…`, `chore/…`, `docs/…`.
- Do the whole task on the branch, commit, push, then STOP. Never merge into `main` yourself — the human reviews the branch and explicitly instructs the merge.
- `main` stays deployable at all times. Tag a known-good build at the end of each working day.
