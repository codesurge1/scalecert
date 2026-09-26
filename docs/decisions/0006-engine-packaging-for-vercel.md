# 0006 — Package `engine/` into the deployed backend function via a build-time copy

## Status

Accepted

## Context

`engine/` lives at the repo root, a sibling of `backend/` and `frontend/`, by design (ADR-0005 area: engine purity, one source of truth for the calculation core). Vercel builds the `backend` Service with `services.backend.root: "backend/"` — that directory is the function's bundle boundary. `engine/` is outside it, so the deployed function crashed at import time on every authed route: `ModuleNotFoundError: No module named 'engine'`. This was flagged as a known follow-up when the Weighing contracts were added (they `from engine... import`) and confirmed as the actual production failure once routes existed and were deployed.

Three candidate fixes were considered:
1. **`includeFiles`** on the service's `functions` config, pointing at the sibling `engine/**`. Vercel's classic (pre-`services`) Python `includeFiles`/`excludeFiles` resolves globs relative to the project root (confirmed from `vercel/vercel` PR #5030's own monorepo example). Whether that remains true once nested under `services.backend.functions` — i.e., whether a service can reach a glob *outside* its own declared `root` at all — could not be confirmed from any source reachable from this sandbox (`vercel.com` and several third-party mirrors are egress-blocked); the closest primary reference found (a `vercel/vercel-plugin` PR migrating `experimentalServices` docs) explicitly does not detail cross-root file access. If the glob turns out to be sandboxed to the service's own root, this fix would fail *silently* — the glob matches nothing, no error, same crash on next deploy.
2. **Make `engine/` a pip-installable local package** (add a `pyproject.toml`, `pip install -e ../engine` via the service's `installCommand`). Works in principle, but is more invasive than needed: it adds packaging metadata to a package whose one hard rule is minimalism (CLAUDE.md: engine purity, zero runtime deps), and changes how `engine` resolves for local tests too (editable-install `sys.path` entries vs. the current plain directory-on-`sys.path` scheme `backend/tests/conftest.py` and root `tests/conftest.py` both already rely on).
3. **A build-time copy** — the service's own `installCommand` runs `cp -r ../engine ./engine` before installing Python dependencies. Mechanically simple, no dependence on unconfirmed glob-sandboxing behavior, and a wrong assumption here (that the service's build step has the sibling directory available one level up) fails *loudly* — `cp` errors out in the build log — rather than silently.

## Decision

Use option 3. `services.backend.installCommand` in `vercel.json` is set to `"cp -r ../engine ./engine && pip install -r requirements.txt"` (this fully replaces whatever install step Vercel would otherwise run, so the explicit `pip install` is required, not optional). `backend/engine/` is gitignored — it is a build-time-generated copy, regenerated on every install, never a second checked-in source of truth for the engine.

Locally verified (this sandbox has no Vercel deploy access, so this is as far as it goes): copying the real repo's `backend/` into an isolated temp directory with no `engine/` present reproduces the exact reported error (`ModuleNotFoundError: No module named 'engine'`). Applying the same `cp -r ../engine ./engine` step (with a real sibling `engine/` copied in at the parent level, matching the actual monorepo layout) makes `from engine.types import AccuracyClass` resolve, a real `engine.weighing.compute_weighing_result` call succeed, and — going further — the actual `backend/main.py` → `app.main:app` FastAPI app (with a fresh venv install of `backend/requirements.txt`, dummy Supabase env vars) import and boot cleanly from within that simulated function root, listing all real routes.

**Not verified, and cannot be from this sandbox:** whether Vercel's real build infrastructure, when building the `backend` service with `root: "backend/"`, actually executes `installCommand` with the sibling `engine/` directory present one level up (i.e., whether `root` only sets that service's build cwd, or produces an isolated/sparse checkout that excludes siblings). The local simulation proves the *mechanism* is correct given that precondition; only a real deploy proves the precondition itself.

## Consequences

- If the precondition holds (full monorepo checked out per service, `root` only changes cwd — the well-established pre-`services` Vercel monorepo behavior, and nothing found suggests `services` changed it), this fix resolves the crash with a minimal, loudly-failing, easily-inspected build step.
- If the precondition does *not* hold, the build itself fails clearly (`cp: cannot stat '../engine'`) rather than deploying a function that 500s at request time — a strictly better failure mode than the status quo, and a fast, unambiguous signal to fall back to option 2 (pip-installable local package) or revisit option 1 with Vercel support/docs once reachable.
- `engine/`'s own purity and its existing test-import path (`tests/conftest.py`) are completely untouched — this is a deploy-only change.
- The real acceptance test is the next preview deploy actually returning 200s on authed routes instead of 500s; this ADR does not close that loop, it only removes the last locally-verifiable blocker to it.
