from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.supabase_client import user_client

app = FastAPI(title="ScaleCert API — walking skeleton")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization.split(" ", 1)[1]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/whoami")
def whoami(authorization: str | None = Header(default=None)):
    token = _bearer_token(authorization)
    client = user_client(token)
    rows = client.table("profiles").select("id, role, full_name").execute().data

    # RLS fails silently: zero rows is a valid, non-error outcome (a misauthored
    # policy looks identical), so it is reported as such rather than as a 404.
    if not rows:
        return {"rls": "applied", "profile": None, "note": "no visible row"}
    return {"rls": "applied", "profile": rows[0]}


@app.get("/whoami/debug")
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
