import sys
from pathlib import Path

import pytest

# Make both the repo-root `engine` package and `backend`'s own `app` package
# importable regardless of the directory pytest is invoked from.
_BACKEND = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND.parent

for path in (_REPO_ROOT, _BACKEND):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(autouse=True)
def _public_app_base_url(monkeypatch):
    """Every real deployment must set `PUBLIC_APP_BASE_URL`
    (fix/certificate-generation-wiring) — `app/routers/sessions.py`'s
    `_verify_url()` now raises rather than silently falling back to a
    possibly-wrong `request.base_url` behind Vercel's two-service split
    (docs/runbook.md). Set a sane default here so the suite behaves like a
    correctly-configured deployment by default; the one test that needs it
    UNSET (the "fails loudly" test itself) overrides this with its own
    `monkeypatch.delenv`.
    """
    monkeypatch.setenv("PUBLIC_APP_BASE_URL", "https://scalecert.example.test")
