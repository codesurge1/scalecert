# Error Log

Purpose: an append-only log of bugs that took real debugging to solve. Each entry captures symptom → root cause → fix → prevention, so the next cold session (human or Claude) doesn't re-debug a problem that's already been solved.

Append new entries at the bottom. Never edit or delete a past entry.

---

### [YYYY-MM-DD] Template entry title

**Symptom:** What was observed (error message, wrong behavior, failing test).

**Root cause:** What actually caused it, once found.

**Fix:** What change resolved it.

**Prevention:** How to avoid this class of bug going forward (a test, a check, a rule added elsewhere).

---

### [2026-09-27] Deep links (and the public verify QR URL) 404 in production

**Symptom:** Navigating inside the app worked fine (clicking links, buttons), but loading any URL directly in a fresh tab — `/instruments`, `/sessions/<id>`, and critically `/verify/{certificate_number}` (the exact URL a certificate's QR code encodes) — returned a 404 from the server. Only `/` loaded directly.

**Root cause:** `vercel.json`'s catch-all rewrite, `{"source": "/(.*)", "destination": {"service": "frontend"}}`, forwards the *exact requested path* to the frontend service and serves whatever real file matches it — index.html at `/` (an implicit directory index), a hashed file under `/assets/*`, `favicon.svg`, and so on. There is no file literally named "instruments" or "verify" in the Vite build output, so any path that isn't a real static file 404s. This is not a Vercel platform bug — it's the well-documented, expected behavior for a Vite SPA on Vercel without an explicit SPA-fallback rule (Vite, unlike some other frameworks Vercel auto-detects, does not get one for free); it just wasn't in place for this project's `services`-shaped `vercel.json`, and `docs/architecture.md` had incorrectly documented the existing rule as already providing "SPA fallback" when it never actually rewrote anything to `index.html`.

**Fix:** Added the missing `path` override to the destination object: `{"service": "frontend", "path": "/index.html"}`. A real static file (matched by an actual path in the frontend build output) still resolves and serves normally, taking precedence over the rewrite; anything else falls back to `index.html`'s content at the originally-requested URL, so React Router picks up the route client-side instead of the server ever needing to know about it. `/api/:path*` is a separate, earlier rule in the same array and is untouched.

**Prevention:** `docs/architecture.md`'s one-domain-routing section now spells out exactly what the `path` override does and why the earlier (undocumented-as-buggy) shape looked like it worked — client-side navigation never exercises the "load a deep link fresh" code path, so this class of bug is easy to ship without noticing in normal day-to-day development. The verification steps in the `fix/spa-deep-link-routing` branch reply (load `/instruments`, `/sessions/<id>`, `/verify/<cert>` directly in a fresh tab; confirm `/api/health` still returns JSON; confirm the page's actual JS/CSS loaded, not just some HTML) are the acceptance check for this class of regression on every future `vercel.json` change to the frontend rewrite.

---

### [2026-09-27] UPDATE 2 — attempt 2 (plain-string root destination) took the WHOLE SITE down; reverted; fix moved to a service-scoped file

**Symptom:** After the `path`-override fix above still 404'd on deep links (see UPDATE above — the `{service, path}` object form doesn't trigger fallback), the root catch-all was changed to a plain string destination: `{"source": "/(.*)", "destination": "/index.html"}`, per Vercel's own Vite framework doc example. This took down the ENTIRE production site, including `/` itself — Vercel's own `404 NOT_FOUND` (with an edge request id) on every route, not just deep links.

**Root cause:** Vercel's Vite-doc example (`{"source": "/(.*)", "destination": "/index.html"}`) is written for a SINGLE-service project, where `index.html` lives at the project root after the build. This project uses the multi-service `services` config model — the frontend's build output, including `index.html`, lives inside the `frontend` service's own directory tree, not the project root. A bare `/index.html` destination has nothing at the project root to resolve to, so every request that hit the catch-all (i.e., everything except `/api/*`) 404'd, including `/`.

**Fix (immediate):** Reverted via `git revert -m 1` of the merge that introduced the plain-string destination (branch `fix/spa-fallback-correct-syntax`), restoring the root catch-all to attempt 1's object form, `{"service": "frontend", "path": "/index.html"}` — service unaffected, root config untouched by this task.

**Fix (this task, `fix/frontend-spa-fallback`) — move the fallback into a service-scoped file.** Added `frontend/vercel.json` (containing only `{"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]}`), on the theory that a rewrite scoped to the `frontend` service's own root directory resolves `/index.html` against THAT service's build output, where the file genuinely exists — unlike the project root, where attempt 2 proved it doesn't. The root `vercel.json` is left exactly as-is (attempt 1's form); this task does not touch it.

**This mechanism is NOT confirmed from a primary source** — `vercel.com` and `openapi.vercel.sh` remain egress-blocked from this sandbox (retried for this task). Vercel's own reference example for this exact stack, [`vercel/examples/services/vite-fastapi`](https://github.com/vercel/examples/tree/main/services/vite-fastapi) (fetched via GitHub, both the raw `vercel.json` and the README), uses NEITHER a per-service `vercel.json` NOR a `path` override — its root config is just `{"source": "/(.*)", "destination": {"service": "frontend"}}` — and its demo app has no client-side routes, so it never exercises this bug at all; it is not a valid precedent either way for THIS specific problem.

**What web search did turn up (third-party, not vercel.com — treat with the same "confirmed vs. inferred" caution as UPDATE above):** two independent real projects that hit and fixed this exact class of bug (Vercel Services + SPA deep-link 404s), both very recently (one PR merged 2026-09-19):
- [MACantara/Phalanx-Cyber-Academy#465](https://github.com/MACantara/Phalanx-Cyber-Academy/pull/465) — merged. Fix: added `"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]` as a property **nested inside `services.frontend` in the root `vercel.json`** (alongside that service's existing `root`/`buildCommand`/`outputDirectory` keys) — NOT a separate file.
- VictorBravo9er/Teacher-Assistant-Workspace#18 and #19 — same nested-in-`services.frontend` pattern in the root config (plus `cleanUrls: false`, to stop the explicit `.html` fallback from being rewritten again by clean-URL handling). This repo ALSO added a `frontend/vercel.json` with the same rewrite, but described it as being for deploying `frontend/` as its own **standalone** Vercel project — a different scenario from a services-monorepo deploy — so it does not confirm Vercel merges a per-service file into a services build; it's evidence for a different deployment mode entirely.

Both real-world examples converge on the SAME mechanism — a `rewrites` property nested inside the service's own block in the ROOT config — and NEITHER uses the `frontend/vercel.json`-file approach this task implements as a Vercel-`services`-model mechanism. This is meaningfully strong (if still not primary-source) evidence that the alternative below may be more likely to work than what this task shipped.

**The one alternative to try if `frontend/vercel.json` fails (a service-level root-config setting):** delete `frontend/vercel.json` and instead add a `rewrites` array directly inside `services.frontend` in the ROOT `vercel.json`:
```json
"services": {
  "frontend": {
    "root": "frontend/",
    "framework": "vite",
    "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
  },
  ...
}
```
This is the one change NOT made in this task (scope was `frontend/vercel.json` + docs only) — it requires editing the root `vercel.json`, which this task was told to leave untouched without an explicit follow-up instruction.

**Also flagged, not acted on:** it's unclear whether the root catch-all's `path: "/index.html"` override (untouched by this task) does anything at all — it demonstrably did not produce SPA fallback in attempt 1's real deploy, yet real static assets kept loading throughout, which is only consistent with it being a no-op for this purpose. Neither working real-world example above uses a `path` key. Recommend dropping it once a working fallback is confirmed by deploy — not changed here.

**Prevention:** Two outages from the same underlying root cause (guessing at a destination shape instead of confirming one) — the general lesson from UPDATE above (trust a primary source over an inference) held, but this time there was no primary source available AT ALL, only conflicting third-party signals. The check order for the next deploy, in every case: `/` loads first (would have caught attempt 2 immediately), then `/api/health` returns JSON, then `/instruments` loads styled (real JS/CSS, not bare HTML), then `/verify/<cert>`. Checking `/` first is the cheapest possible smoke test and would have caught attempt 2's outage in seconds rather than needing a full page verification — add this ordering to any future SPA-routing change's rollout checklist.

---

### [2026-09-27] UPDATE 3 — attempt 3 (`frontend/vercel.json`) deployed and STILL 404'd on deep links; switched to the mechanism proven by real-world Vercel Services deployments

**Symptom:** After attempt 3 shipped (a standalone `frontend/vercel.json` scoping the SPA rewrite to the frontend service's own root — see UPDATE 2), `https://scalecert-alpha.vercel.app/instruments` still returned a 404 on a fresh direct load. Confirmed by the user directly hitting the URL post-deploy.

**Root cause:** The per-service-`vercel.json`-file mechanism attempt 3 bet on was explicitly flagged as unconfirmed when it shipped (see UPDATE 2's "NOT confirmed from a primary source" section) — Vercel evidently does not read/merge a `frontend/vercel.json` into a `services`-model deploy the way a standalone single-project deploy would. The file was silently ignored; the frontend service kept whatever the top-level rewrite handed it, same as attempt 1.

**Fix:** Removed `frontend/vercel.json` entirely. Moved the SPA rewrite to the mechanism UPDATE 2 had already identified, from real evidence, as more likely correct: a `rewrites` array nested as a property **inside `services.frontend`** in the root `vercel.json`, alongside its existing `root`/`framework` keys — not a separate file, and not a `path` override on the top-level catch-all (which is reverted to the bare `{"service": "frontend"}` form; the `path` key never demonstrably did anything across three attempts and is dropped). Full root `vercel.json` after this fix:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "regions": ["bom1"],
  "services": {
    "frontend": {
      "root": "frontend/",
      "framework": "vite",
      "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
    },
    "backend": {
      "root": "backend/",
      "entrypoint": "main:app",
      "installCommand": "cp -r ../engine ./engine && pip install -r requirements.txt"
    }
  },
  "rewrites": [
    { "source": "/api/:path*", "destination": { "service": "backend" } },
    { "source": "/(.*)", "destination": { "service": "frontend" } }
  ]
}
```
This exact shape — rewrite nested in the service block, no `path` override at the top level — matches two independent real projects that hit and fixed this identical bug: [MACantara/Phalanx-Cyber-Academy#465](https://github.com/MACantara/Phalanx-Cyber-Academy/pull/465) (merged) and VictorBravo9er/Teacher-Assistant-Workspace#18/#19 (both found via web search in the prior task, re-used here since this is exactly the alternative UPDATE 2 already flagged).

**Still not confirmed from Vercel's own primary docs** — `vercel.com`/`openapi.vercel.sh` remain egress-blocked. This is the best-evidenced option available (two independent real, working deployments using this exact shape), not a certainty. The deploy is still the test.

**Prevention:** Four attempts, one outage, to fix one rewrite — the actual lesson is that this project's specific combination (Vercel `services` config + Vite + SPA client-side routing) has no confirmable primary-source answer available from this sandbox, only real-world precedent. Future changes to this rewrite should be validated against a real deploy immediately (check order: `/`, then `/api/health`, then `/instruments` styled, then `/verify/<cert>`) rather than reasoned about further in the abstract — the next failure signal is itself useful data, not a reason to keep guessing at new destination shapes without a stronger source.

---

### [2026-09-28] An approver opening a submitted session sees it flash then break with a 409, instead of the data they're supposed to review

**Symptom:** A technician submits a session (`draft → submitted`). An approver opens it to review: the session overview (or a Damp heat/Endurance test page) renders for a split second — then the whole view is replaced by a generic "Couldn't load this session" error card with a Retry button, discarding everything that had already loaded (session, instrument, every already-submitted reading). The approver has no way to see what they're supposed to approve.

**Root cause:** Three page-mount effects — `SessionPage.jsx` (the overview) and `DampHeatSessionPage.jsx`/`EnduranceSessionPage.jsx` (clauses 13/15) — bundled the draft-only `POST .../damp-heat/setup` and/or `POST .../endurance/setup` calls into the SAME `Promise.all` as their essential read-only fetches (session, instrument, sequence, every test's readings). Those setup endpoints auto-provision Damp heat's fixed a/b/c runs (or Endurance's a/c runs) and are correctly gated to `status = 'draft'` on the backend (`ensure_session_is_draft` in `app/routers/sessions.py`, backed by `runs_write`'s `status = 'draft'` requirement in `db/schema.sql`) — they 409 by design on a submitted/approved/issued session. `Promise.all` rejects the WHOLE batch the instant any one promise rejects, and each of these three effects' shared `.catch()` unconditionally ran `setError(err.message); setSession(null);` — blanking the entire page on that single 409, even though the session/instrument/readings had already loaded successfully. There was no separate read-only way to learn which Damp heat/Endurance runs already exist (unlike Weighing, which already has a genuinely read-only `GET /weighing/runs` alongside its user-action-gated `POST /weighing/runs`) — the ONLY way to list them was the same combined "create-then-list" `POST .../setup` endpoint, so a page could not avoid calling it just to render read-only. Every other test page (Weighing, Zero-tare, Repeatability, Eccentricity, Discrimination, Sensitivity, Tilting, Voltage variations, all seven clause-12.x disturbance tests) was already clean — GET-only on mount, no draft-gated write ever fires from a page load.

**Fix (`fix/no-draft-writes-on-readonly-session`):**
1. **Never call a draft-only write from a mount effect on a non-draft session.** Added `GET /sessions/{id}/damp-heat/runs` and `GET /sessions/{id}/endurance/runs` (`app/routers/sessions.py`) — read-only listings backed by the already-existing, already-unrestricted `runs_repo.list_runs()` (the `runs_select` RLS policy has no draft requirement — reads are already fine for the session's creator/approver/admin regardless of status; only `runs_write`, which these new endpoints never touch, is draft-gated). `SessionPage.jsx`, `DampHeatSessionPage.jsx`, and `EnduranceSessionPage.jsx` now branch on `session.status === "draft"`: call the auto-provisioning `POST .../setup` only when draft, call the new read-only `GET .../runs` otherwise. A non-draft session's Damp heat/Endurance page that has zero recorded runs (the technician never opened it while still draft) now shows "No Damp heat/Endurance runs have been recorded for this session" instead of either an infinite spinner or a blanked page.
2. **A single failed optional/secondary fetch must never blank the whole page.** `SessionPage.jsx`'s big per-test `Promise.all` (20 read-only fetches plus the two now-conditional runs fetches) was changed to `Promise.allSettled`, with each of the ~22 setters falling back to an empty/null value on that one item's rejection. The page's `.catch()` — the one that sets the fatal `error`/`session = null` state — is now reachable only by a genuine failure of the PRIMARY `GET /sessions/{id}` fetch itself, never by any secondary per-test read.

**Prevention:** Never auto-fire a draft-only write from a component's mount effect — gate it on the session's actual current status (`session.status === "draft"`), exactly the same discipline `useWeighingReadings.js`'s `disabled = sessionStatus !== "draft"` already applies to user-triggered writes. When a page's mount effect needs BOTH essential reads and one or more optional/secondary reads (or draft-gated auto-provisioning calls) in the same batch, use `Promise.allSettled`, not `Promise.all` — a 409 (or any other single failure) on an optional item must degrade that one piece of state, never cascade into `setSession(null)` and blank data that already loaded successfully. Regression tests: `backend/tests/routers/test_damp_heat_router.py`/`test_endurance_router.py` assert the new `GET .../runs` endpoints succeed on a non-draft session without ever calling `insert_run`, alongside the pre-existing assertion that `POST .../setup` still correctly 409s on a non-draft session (that guard is intentional and untouched — the fix is entirely that the frontend stopped calling it when it shouldn't).

---

### [2026-09-28] An approver reviewing a submitted session sees the page-9 summary but has no way to open any test

**Symptom:** An approver opens a session a technician submitted, to review it before approving or returning it. The page-9 "Summary of type evaluation" summary table renders with correct PASSED/FAILED/Remarks data for every implemented test — but nothing on the page looks or acts like a button: no visible "Open"/"View" affordance anywhere, and the approver could not tell that any row could be clicked. They had to approve or return the certificate without being able to inspect the actual recorded readings behind any test — unacceptable for a review role.

**Root cause — NOT what it looked like.** The natural hypothesis (and the one this task started from) was that `SessionSummaryTable.jsx`'s row clickability was gated on session status or role — e.g. `status === 'draft'`, or a "test is startable" check that only holds for a technician on a draft session. Reading the actual code (`RowLabel`/`SummaryRowGroup` in `SessionSummaryTable.jsx`, `TEST_ROWS`/`isSelectable` in `testChecklist.js`) disproved that: an implemented, applicable test's row has ALWAYS been a real `<Link>` to that test's route regardless of `session.status` or the viewer's role — neither function has ever taken a `session`, `status`, or `role` parameter, and `db/schema.sql`'s `sessions_select`/`runs_select`/`readings_select`/`results_select` RLS policies have always permitted an approver/admin to read a session's full data at any status, not just draft. **The actual bug was pure affordance:** the only visual signal that a row was interactive was its label rendering in `text-primary` with an underline that appeared only on hover — inside a dense, ~40-row, black-and-white, serif "printed form" table where every other cell is also just colored/plain text. There was nothing resembling a button, an icon, a highlighted row, or any other UI convention this app uses elsewhere (e.g. `InstrumentsListPage`'s bordered "View" button, `FocusedPageHeader`'s bordered back-arrow chip) to signal "this is clickable." An approver scanning the table for a way to open a test had nothing to visually anchor on — the report of "no button, no clickable row, nothing" was accurate to what a viewer could perceive, even though the code was never gating anything.

**Fix (`fix/approver-can-open-tests`):**
1. Extracted the openability decision into its own pure function, `src/lib/rowOpenable.js`'s `isRowOpenable(sub, instrument)` — deliberately accepting no `session`/`status`/`role` parameter, so this guarantee can't be silently reintroduced by a future change without altering every call site's signature. `SessionSummaryTable.jsx` now calls this one function instead of re-deriving the same logic inline.
2. Made the affordance impossible to miss: a small bordered "Open →" chip next to every openable row's label (`OpenChip`, deliberately sans-serif and un-form-styled, so it reads as a UI control rather than page content), plus the entire row (not just the label text) is now hover-highlighted, shows `cursor-pointer`, and navigates on click (`onClick` → `useNavigate()`, skipped when the click already landed on the real `<a>` to avoid a redundant double-navigation).
3. N/A rows stay inert (not opened to an explanatory view) — deliberate: an N/A test has nothing recorded, so there's nothing for a viewer to review by opening it; the reason text already answers the only question that row can raise.
4. Audited every implemented test's session page (Weighing, Zero-tare, Repeatability, Eccentricity, Discrimination, Tilting, Sensitivity, Voltage variations, all seven clause-12.x disturbance tests, Damp heat, Endurance) and `RunSelector.jsx` for the same class of bug — confirmed all already render correctly read-only for a non-creator/non-draft viewer (the "not draft — read-only" banner, disabled inputs, and RLS-permitted reads were all already correct, largely from `fix/no-draft-writes-on-readonly-session` immediately above and earlier feature work) — no changes needed there.

**Prevention:** A UI bug report of "I can't find any way to do X" does not always mean X is gated in code — verify the actual gating logic FIRST (here, reading `RowLabel`/`isSelectable` immediately disproved the assumed root cause), and if it isn't gated, look for a pure discoverability/affordance problem instead of "fixing" a status check that was never wrong. When a row/element's interactivity must never depend on a particular piece of state (here: session status, viewer role), express that as a function that structurally cannot accept that state as a parameter (`isRowOpenable(sub, instrument)`, no `session` argument) rather than as a comment promising the caller won't pass it — a parameter that doesn't exist can't be misused. `frontend/src/lib/rowOpenable.test.js` (the first frontend test in this repo — `docs/testing.md`, Vitest) locks this in with an explicit `isRowOpenable.length === 2` assertion, so a future PR that tries to add a status/role gate has to touch a failing test, not just a comment.
