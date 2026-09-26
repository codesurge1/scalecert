import os

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import AuthContext, get_auth_context
from app.routers.instruments import router as instruments_router
from app.routers.sessions import router as sessions_router

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

# Mounted under /api so every route is reachable at /api/..., matching the
# public path Vercel's rewrite forwards to this service (see /vercel.json),
# which sends the full incoming path through rather than stripping the prefix.
api = APIRouter(prefix="/api")


@api.get("/health")
def health():
    return {"status": "ok"}


@api.get("/whoami")
def whoami(auth: AuthContext = Depends(get_auth_context)):
    rows = auth.client.table("profiles").select("id, role, full_name").execute().data

    # RLS fails silently: zero rows is a valid, non-error outcome (a misauthored
    # policy looks identical), so it is reported as such rather than as a 404.
    if not rows:
        return {"rls": "applied", "profile": None, "note": "no visible row"}
    return {"rls": "applied", "profile": rows[0]}


@api.get("/whoami/debug")
def whoami_debug(auth: AuthContext = Depends(get_auth_context)):
    rows = auth.client.table("profiles").select("id, role, full_name").execute().data

    # Expected with correct RLS: a technician sees exactly 1 row (their own, via
    # profiles_select_own's `id = auth.uid()` clause); an approver sees every row
    # (the same policy's `get_my_role() in ('approver','admin')` clause). That
    # 1-vs-many split is the visible proof RLS is applying per-caller.
    my_role = rows[0]["role"] if rows else None
    return {"rls": "applied", "visible_profile_count": len(rows), "role": my_role}


api.include_router(instruments_router)
api.include_router(sessions_router)

app.include_router(api)
