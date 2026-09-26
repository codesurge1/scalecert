import os

from fastapi import APIRouter, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.supabase_client import user_client

app = FastAPI(title="ScaleCert API — walking skeleton")

# Same-origin in production (frontend and backend share one Vercel domain via
# Vercel Services, routed by /vercel.json) means CORS isn't needed there at all.
# This middleware exists only for local dev, where the Vite dev server (5173)
# and uvicorn (8000) are different origins. Configurable via env rather than a
# wildcard, so a stray "*" is never sitting in the code once it stops being useful.
CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ALLOW_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mounted under /api so the three routes are reachable at /api/health,
# /api/whoami, /api/whoami/debug — matching the public path Vercel's rewrite
# forwards to this service (see /vercel.json), which sends the full incoming
# path through rather than stripping the prefix.
api = APIRouter(prefix="/api")


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization.split(" ", 1)[1]


@api.get("/health")
def health():
    return {"status": "ok"}


@api.get("/whoami")
def whoami(authorization: str | None = Header(default=None)):
    token = _bearer_token(authorization)
    client = user_client(token)
    rows = client.table("profiles").select("id, role, full_name").execute().data

    # RLS fails silently: zero rows is a valid, non-error outcome (a misauthored
    # policy looks identical), so it is reported as such rather than as a 404.
    if not rows:
        return {"rls": "applied", "profile": None, "note": "no visible row"}
    return {"rls": "applied", "profile": rows[0]}


@api.get("/whoami/debug")
def whoami_debug(authorization: str | None = Header(default=None)):
    token = _bearer_token(authorization)
    client = user_client(token)
    rows = client.table("profiles").select("id, role, full_name").execute().data

    # Expected with correct RLS: a technician sees exactly 1 row (their own, via
    # profiles_select_own's `id = auth.uid()` clause); an approver sees every row
    # (the same policy's `get_my_role() in ('approver','admin')` clause). That
    # 1-vs-many split is the visible proof RLS is applying per-caller.
    my_role = rows[0]["role"] if rows else None
    return {"rls": "applied", "visible_profile_count": len(rows), "role": my_role}


app.include_router(api)
