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
