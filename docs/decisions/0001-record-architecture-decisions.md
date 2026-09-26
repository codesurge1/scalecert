# 0001 — Record architecture decisions

## Status

Accepted

## Context

ScaleCert will accumulate non-trivial, hard-to-reverse choices about schema, auth, the engine, and process. Without a durable record, cold sessions (and future contributors) re-litigate decisions already made, or silently violate constraints whose rationale was never written down.

## Decision

All non-trivial or hard-to-reverse decisions are recorded as numbered Architecture Decision Records (ADRs) in `/docs/decisions/`, using this file's format (Status, Context, Decision, Consequences).

ADRs are append-only: a past ADR is never edited to change its decision. If a decision changes, a new ADR is added that supersedes the old one, referencing it explicitly (and the old ADR's Status is updated to note it was superseded, linking to the new one).

## Consequences

- The decision history is traceable in order, without rewriting the past.
- Every new non-trivial decision requires a small amount of extra writing (a new ADR file) before or alongside the change that implements it.
- `/docs/architecture.md` and other docs describe the current state; ADRs describe *why* that state was chosen and *when* it changed.

---

## Template for future ADRs

```markdown
# NNNN — Title

## Status

Proposed | Accepted | Superseded by NNNN

## Context

## Decision

## Consequences
```
