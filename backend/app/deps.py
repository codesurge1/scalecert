"""The reusable auth dependency every data-touching route depends on.

Extracts the caller's JWT (same header `/whoami` already reads), builds the
per-request user-scoped Supabase client from it (never the service-role key —
CLAUDE.md), and resolves the caller's user id via GoTrue's `get_user`, so
every route that needs `auth.uid()` for an insert payload (`registered_by`,
`created_by`, `entered_by`, `actor_id`) has it without re-deriving it.
"""

from dataclasses import dataclass

from fastapi import Header, HTTPException
from supabase import Client

from app.supabase_client import user_client


@dataclass(frozen=True)
class AuthContext:
    client: Client
    user_id: str
    token: str


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization.split(" ", 1)[1]


def get_auth_context(authorization: str | None = Header(default=None)) -> AuthContext:
    """FastAPI dependency: `Depends(get_auth_context)`. Raises 401 for a
    missing, malformed, or invalid/expired token — never lets a request
    through without a resolved user id."""
    token = _bearer_token(authorization)
    client = user_client(token)

    user_response = client.auth.get_user(token)
    if user_response is None or user_response.user is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    return AuthContext(client=client, user_id=user_response.user.id, token=token)
