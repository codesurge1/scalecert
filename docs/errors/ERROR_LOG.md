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
