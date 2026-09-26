# Vercel Services entrypoint shim.
#
# Vercel resolves a Python service's "entrypoint" (vercel.json: services.backend.entrypoint)
# as a "module:attr" import string, module-name relative to the service root ("backend/").
# The confirmed-working convention (github.com/vercel/examples/tree/main/services/vite-fastapi)
# is a plain main.py sitting directly at that root. This file just re-exports the real
# app (kept in app/main.py, which is what `uvicorn app.main:app` uses for local dev)
# so the deploy wiring doesn't require restructuring the actual application package.
from app.main import app  # noqa: F401
