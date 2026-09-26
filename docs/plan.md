# ScaleCert — Build Plan

The sequencing layer for the 3-day rebuild. Scope, architecture, and per-test domain detail live in `architecture.md`; this file is about order-of-operations and integration risk. Hard rules live in `CLAUDE.md`.

## Five principles
1. **Two tracks from hour zero — don't serialize them.** The infra track (Vercel Services, Supabase, auth) is the riskiest, least-familiar work: it gets its own owner and a generous, untimed budget, and must not block anyone. The engine track is pure Python with zero infra dependencies, so it starts immediately and is built/tested locally with nothing deployed. Front-load the intellectual core because it's also the lowest-risk work.
2. **Walking skeleton before depth (infra track's first goal).** First deliverable is a thin end-to-end round-trip on real infra — React → FastAPI → Supabase → back — with no test logic. Discover the deployment story in hour 2, not on day 3.
3. **One vertical slice before seven.** Build Weighing straight through every layer before touching the other tests. Weighing is the right slice: hardest reading shape (bidirectional), and its formula family is reused by Eccentricity, Tilting, and the zero/tare variant.
4. **Contracts first, then parallelize.** The Pydantic models (reading-input and result shape, per test_type) are the interface between all lanes. Write the signatures first, as stubs, so every lane builds against them without blocking.
5. **Always shippable.** Keep `main` deployable at all times; tag a known-good, demo-able build at the end of every day. If day 3 breaks, demo yesterday's tag.

## Phase 0 — Walking skeleton + scary infra
Owned infra track, generous budget (the original "3 hours, whole team" estimate was fiction — unfamiliar infra on the critical path). Engine track runs in parallel from the same hour.
- Stand up the new Supabase project; run the migration (with the four schema patches).
- **Configure the Postgres connection pooler (Supavisor, transaction mode)** — not optional on serverless.
- Vercel Services deploying both builds to one domain with a `/health` endpoint.
- Supabase Auth login; prove one authenticated, user-scoped call reaches FastAPI and acts as that user against Postgres with RLS applying.
- `handle_new_user` trigger; a "who am I / what can I see" debug endpoint.
- **Exit criteria:** migration applied; pooler configured; both builds on one domain; authenticated user-scoped round-trip with RLS enforced; who-am-I endpoint works; two demo accounts (technician + approver) seeded with correct roles.

## Phase 1 — Contract + engine spine (test-first, hour zero)
- Write the worked example as a failing pytest first (Class III, e=1g, initial: 300g → mpe ±0.5g; 300.4g PASS, 300.6g FAIL). Build the MPE lookup and change-point calc until green.
- **One example is a smoke test, not validation.** Build a boundary-value test table — every MPE band edge from both sides, Max, Min, both directions, initial and in-service-doubled — green before any engine number is trusted. The test suite is the project's credibility.
- Write all seven Pydantic model signatures as stubs to unblock the lanes.
- Enforce engine purity via an import check in CI from the first commit.
- **Load count is 5, not 10**, for the 8.3.3 verification scope (the "≥10" in the visit report is the full type-evaluation figure).

## Phase 2 — Weighing vertical slice, end to end
Engine (bidirectional, auto-generated load sequence — technician enters only I and ΔL) → Pydantic models → `POST /sessions/{id}/readings` (validate, compute, write raw reading + result together) → DB + RLS → frontend form → full-derivation result display (L, I, ΔL, E, Ec, E0, mpe, margin — not just PASS/FAIL) → submit → approve by a different user → PDF to Supabase Storage with QR → public `/verify/{cert}`.
**Exit:** register → weigh → submit → switch user → approve → issue → scan QR → public verify page. Own the Band-1 open item aloud: "deterministic and reproducible, pending RRSL's confirmed convention," never "placeholder."

## Phase 3 — Breadth, in leverage order
- **Zero/tare device accuracy** — nearly free (Weighing formula family, flagged variant).
- **Repeatability** — own model: two series, no E0, two independent criteria (per-reading and spread). First truly different shape.
- **Eccentricity (3.1)** — Weighing formula, E0 re-measured before each position (1–4 clockwise).
- **Cut the gated three — Tilting, Discrimination, Sensitivity — from the build; present as "spec'd, not built."** Discrimination is N/A for digital (the common demo case), Sensitivity is non-self-indicating only, Tilting is mobile only — a typical demo instrument is digital and fixed, so none render. Build the four universal tests well; present the three as architecturally supported (selectable, gated, reading forms present) without calc logic.
- Per-session test selector: default universal, offer conditionals by instrument properties, override-with-reason — never silently auto-decide. Tests run in any order.
- **Second forced-integration checkpoint (end of day 2):** every built test through the real API, real DB, real deploy — no mocks. Name one integration owner.

## Phase 4 — Integrity hardening + demo prep
- **Demo path is a protected deliverable — build and rehearse first, not last.** Script and run twice: register → weigh → submit → switch user → approve → issue → QR → verify → discrepancy. Cut breadth before demo polish.
- Adversarial RLS test still green (technician self-approve via direct API call → Postgres `42501`).
- Append-only audit log — the cheap, robust 90%: `data` column populated, RLS enforcing no-UPDATE/no-DELETE, failed audit write surfaces a visible warning.
- Hash chain is the stretch, not core: a broken chain reads as tampering, worse than none. If built: numbers-as-strings before hashing, sorted keys, fixed-precision UTC-Z timestamps, omit-missing-keys.
- Regulatory grounding for the pitch: R76-2 §17.4 makes the audit-trail/checksum design an OIML requirement — frame as "we implement what §17.4 mandates," not "§17.4 specifies a hash chain."

## Lanes
Assumes ~5–6 people. At four, pair up (engine+API, frontend+PDF/verify) and lean on the vertical slice. Name an integration owner regardless.
- **Engine** — pure package, all in-scope tests, pytest, purity-enforced.
- **API + DB** — routes, RLS, auth-JWT flow, audit chain; owns the `42501` tripwire.
- **Frontend** — auth, registration, test selector, reading forms, derivation display.
- **PDF + public verify** — reportlab, Storage, QR, login-free verify + discrepancy flow (the differentiator).

## Open questions
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
