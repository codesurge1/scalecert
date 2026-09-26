# Session Log

Purpose: an append-only log of working sessions on ScaleCert, so any session (cold or continuing) can quickly see what changed recently, what's next, and what's still open. Read the last 2–3 entries at the start of every session; append a new entry at the end of every session.

Append new entries at the bottom. Never edit or delete a past entry.

---

### [YYYY-MM-DD] — session summary template

**Done:** What was completed this session.

**Next:** What the following session should pick up.

**Open questions:** Anything unresolved that needs a decision or more information.

---

### [2026-09-26] — seed build plan, branch workflow, ADRs 0002/0003

**Done:** Seeded `docs/plan.md` with the full build plan (five principles, phases 0–4, lanes, open questions). Added the branch-per-task workflow rule to `CLAUDE.md`. Recorded ADR-0002 (new Supabase project) and ADR-0003 (hosting on Vercel with the Supavisor pooler).

**Next:** Schema migration.

**Open questions:**
- Band-1 intermediate load spacing (deterministic placeholder until RRSL confirms).
- Whether the ~17–18 item battery is full type evaluation (assumed yes).
- Repeatability's ~50%/100% load values (working default).
- Admin role-promotion UI vs. seed-script-only (see ADR when decided).
