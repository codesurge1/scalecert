# Testing

Purpose: define the test strategy for the engine, API, and RLS policies.

> STATUS: engine test strategy is authoritative. API tests and RLS adversarial tests are pending their build tasks — do not treat those sections as authoritative yet.

## Test strategy

Pure-Python code (`engine/`) gets pure-Python tests (`tests/`, pytest, standard library only besides pytest itself) — no mocks, no fixtures standing in for FastAPI/Supabase, because the engine never touches either. Per CLAUDE.md: no calculated verdict is trusted on a single worked example — every engine change must keep the boundary-value table green, not just the worked example.

Four files, each with one job:
- `tests/test_worked_example.py` — the canonical Class III / e=1g / initial / 300g example from `docs/plan.md` Phase 1. Written and run to fail *before* `engine/mpe.py` or `engine/weighing.py` existed, then implemented until green — a smoke test, not the validation.
- `tests/test_mpe_boundaries.py` — the actual acceptance criterion (see below).
- `tests/test_input_validation.py` — proves "no silent defaults": every required argument missing, or given the wrong type (e.g. a `float` where `Decimal` is required), raises rather than being guessed.
- `tests/test_purity.py` — mechanical enforcement of the engine-purity guardrail: walks every `engine/*.py` file's AST and fails if any top-level import resolves outside `sys.stdlib_module_names`. Verified to actually catch a violation (a temporary `import fastapi` was added, confirmed to fail the test, then removed) rather than trivially passing.

## Engine boundary-value table

For every accuracy class (I, II, III, IIII) and both `initial`/`subsequent` (same values) and `in_service` (doubled):
- Every R76-1 Table 6 band edge, both sides — e.g. Class III: `m=500` → `0.5e`, `m=501` → `1.0e`; `m=2000` → `1.0e`, `m=2001` → `1.5e`.
- The Max (top of that class's table range) and Min (`m=0`) ends.
- `m` past the top of a *bounded* class's table (II/III/IIII have an explicit ceiling; I does not) raises `ValueError` rather than extrapolating.
- The verdict boundary itself, both directions: `|Ec| == mpe` is an inclusive PASS; the smallest amount over is a FAIL; checked for both positive and negative `Ec`.
- `in_service` doubling actually changing a verdict: the same load and reading that fails against the `initial` mpe passes against the doubled `in_service` mpe.

## API tests

## RLS adversarial tests

## Frontend tests

Added `fix/approver-can-open-tests` — the first frontend test in this repo (`frontend/src/lib/*.test.js`, Vitest, reading `vite.config.js`'s own `test` block — no separate config, so the `@` path alias is shared, not duplicated). Reserved for pure logic that's cheap to isolate from React/routing (e.g. `src/lib/rowOpenable.js`'s `isRowOpenable`) — component rendering isn't covered yet (`environment: 'node'`, no `jsdom`), same "add it when something actually needs it" approach the engine's own test suite took.

```
cd frontend && npm run test
```

## How to run

```
python3 -m venv .venv-engine
.venv-engine/bin/pip install -r requirements-dev.txt
.venv-engine/bin/pytest tests/
```

(Any virtualenv works — `requirements-dev.txt` pins only `pytest`; the engine itself has zero runtime dependencies.)
