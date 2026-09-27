"""Typed repository-layer errors — so a Supabase/PostgREST failure never
escapes a repository function as a bare `IndexError` (on an empty `rows[0]`)
or an unhandled `postgrest.exceptions.APIError`.

Two failure shapes are both covered here, per CLAUDE.md's own guardrail
("RLS fails silently — a misauthored policy returns zero rows, not an
error. Handle both failure shapes: explicit error vs. empty result."):
  - PostgREST returning a non-2xx — an RLS `WITH CHECK`/`USING` clause
    rejected the operation, a malformed id hits a Postgres type error
    (`invalid input syntax for type uuid`), a constraint failed, ...
    -> `postgrest.exceptions.APIError`.
  - An insert "succeeding" (2xx) but returning zero rows — the row WAS
    written, but the caller's own SELECT-after-INSERT visibility (gated by
    the table's SELECT policy) filtered it back out. This is the classic
    silent-RLS case: no exception at all, just an empty result.

Callers catch the one `RepositoryError` type and decide the HTTP response
from `.likely_rls`/`.hint` instead of re-deriving it from a raw `APIError`'s
shape at every call site (or, worse, not catching anything and letting
FastAPI's default handling turn it into an opaque 500 with no detail).
"""

from postgrest.exceptions import APIError

# Postgres error codes PostgREST passes through as APIError.code that
# indicate an RLS/permissions rejection rather than a data/schema problem.
# 42501 = insufficient_privilege (a WITH CHECK/USING clause rejected the
# row); PGRST301 = PostgREST's own "no suitable row" JWT/role class.
_RLS_ERROR_CODES = {"42501", "PGRST301"}


class RepositoryError(Exception):
    """Raised by repository helpers (`run_select`/`run_insert`) instead of
    letting a bare `IndexError` or `postgrest.exceptions.APIError` escape.
    `table`/`operation`/`hint` make the eventual HTTP error's `detail` say
    what failed and why, not just "500". `likely_rls` lets a caller choose
    403 over 500 when the underlying cause looks like a policy rejection.
    """

    def __init__(
        self,
        *,
        table: str,
        operation: str,
        hint: str,
        likely_rls: bool = False,
        cause: Exception | None = None,
    ) -> None:
        self.table = table
        self.operation = operation
        self.hint = hint
        self.likely_rls = likely_rls
        super().__init__(f"{operation} on {table!r} failed: {hint}")
        if cause is not None:
            self.__cause__ = cause


def _is_rls_error(exc: APIError) -> bool:
    return exc.code in _RLS_ERROR_CODES


def run_select(query, *, table: str, hint: str) -> list:
    """Execute a Supabase `.select(...).execute()`-style query. An empty
    result is a normal, valid outcome for a SELECT (nothing matched, or RLS
    filtered it all out) — returned as-is, `[]`, not an error. Only an
    outright `APIError` (a malformed id, a genuine RLS/permissions
    rejection, ...) is translated into a `RepositoryError`, never left to
    escape unhandled.
    """
    try:
        return query.execute().data
    except APIError as exc:
        raise RepositoryError(
            table=table,
            operation="select",
            hint=f"{hint} — PostgREST error {exc.code}: {exc.message}",
            likely_rls=_is_rls_error(exc),
            cause=exc,
        ) from exc


def run_insert(query, *, table: str, hint: str) -> dict:
    """Execute a Supabase `.insert(...).execute()`-style query and return
    its single inserted row. Translates BOTH failure shapes into one
    `RepositoryError`:
      - the call itself raising `APIError` (e.g. a `WITH CHECK` clause
        rejected the row -> Postgres 42501), and
      - the call succeeding but returning zero rows (the row was written,
        but the SELECT-after-INSERT visibility didn't allow it back —
        RLS's silent-failure mode).
    Never lets `rows[0]` throw a bare `IndexError`.
    """
    try:
        rows = query.execute().data
    except APIError as exc:
        raise RepositoryError(
            table=table,
            operation="insert",
            hint=f"{hint} — PostgREST error {exc.code}: {exc.message}",
            likely_rls=_is_rls_error(exc),
            cause=exc,
        ) from exc

    if not rows:
        raise RepositoryError(
            table=table,
            operation="insert",
            hint=(
                f"{hint} — insert returned zero rows; likely an RLS policy silently "
                "rejected it (CLAUDE.md: RLS fails silently)"
            ),
            likely_rls=True,
        )
    return rows[0]


def run_update(query, *, table: str, hint: str) -> dict:
    """Execute a Supabase `.update(...).eq(...)`-style query and return its
    single affected row. Same two-failure-shape translation as `run_insert`:
    an outright `APIError` (a `WITH CHECK` clause rejected the resulting
    row), or a "successful" empty result — for an UPDATE this means the
    row's current state didn't satisfy the policy's `USING` clause, so
    nothing was touched at all. Since every caller here targets one
    specific, already-resolved row by id, a zero-row result is always
    treated as a likely RLS rejection, never a legitimate "nothing to
    update." Never lets `rows[0]` throw a bare `IndexError`.
    """
    try:
        rows = query.execute().data
    except APIError as exc:
        raise RepositoryError(
            table=table,
            operation="update",
            hint=f"{hint} — PostgREST error {exc.code}: {exc.message}",
            likely_rls=_is_rls_error(exc),
            cause=exc,
        ) from exc

    if not rows:
        raise RepositoryError(
            table=table,
            operation="update",
            hint=(
                f"{hint} — update matched/returned zero rows; likely an RLS policy's "
                "USING clause silently excluded it (CLAUDE.md: RLS fails silently)"
            ),
            likely_rls=True,
        )
    return rows[0]


def run_rpc(query, *, table: str, hint: str):
    """Execute a Supabase `.rpc(name, params)`-style query and return its
    scalar `.data`. A Postgres function that itself raises (e.g. a role
    check via `RAISE EXCEPTION ... USING ERRCODE = '42501'`) surfaces here
    as an `APIError` exactly like a rejected INSERT/UPDATE does, so the
    same RLS-code detection applies. Used for `issue_certificate_number()`
    — the one place this app calls a stored procedure rather than a plain
    table operation, since consuming a Postgres sequence atomically has no
    other path through PostgREST's table-only REST surface.
    """
    try:
        response = query.execute()
    except APIError as exc:
        raise RepositoryError(
            table=table,
            operation="rpc",
            hint=f"{hint} — PostgREST error {exc.code}: {exc.message}",
            likely_rls=_is_rls_error(exc),
            cause=exc,
        ) from exc

    if not response.data:
        raise RepositoryError(
            table=table,
            operation="rpc",
            hint=f"{hint} — rpc call returned no value",
            likely_rls=True,
        )
    return response.data
