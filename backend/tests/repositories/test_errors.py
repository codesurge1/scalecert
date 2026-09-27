"""Pure unit tests for app.repositories.errors — no DB, no HTTP. Proves
`run_select`/`run_insert`/`run_update`/`run_rpc` never let a bare
`IndexError` or unhandled `postgrest.exceptions.APIError` escape, for both
failure shapes CLAUDE.md calls out: an explicit PostgREST error, and a
"successful" empty result.
"""

import pytest
from postgrest.exceptions import APIError

from app.repositories.errors import RepositoryError, run_insert, run_rpc, run_select, run_update


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Stands in for a supabase-py query builder: `.execute()` either
    returns a fake response or raises, exactly like the real one."""

    def __init__(self, *, data=None, raises=None):
        self._data = data
        self._raises = raises

    def execute(self):
        if self._raises is not None:
            raise self._raises
        return _FakeResponse(self._data)


def _api_error(code, message="boom"):
    return APIError({"code": code, "message": message, "hint": None, "details": None})


# ---------------------------------------------------------------------------
# run_select
# ---------------------------------------------------------------------------
def test_run_select_returns_data_on_success():
    rows = run_select(_FakeQuery(data=[{"id": "a"}]), table="widgets", hint="listing widgets")
    assert rows == [{"id": "a"}]


def test_run_select_returns_empty_list_as_is_not_an_error():
    # An empty SELECT result is a normal outcome (nothing matched, or RLS
    # filtered it out) — never raised as an error.
    rows = run_select(_FakeQuery(data=[]), table="widgets", hint="listing widgets")
    assert rows == []


def test_run_select_wraps_api_error_never_lets_it_escape():
    query = _FakeQuery(raises=_api_error("22P02", "invalid input syntax for type uuid"))
    with pytest.raises(RepositoryError) as excinfo:
        run_select(query, table="widgets", hint="fetching widget 'bad-id'")
    exc = excinfo.value
    assert exc.table == "widgets"
    assert exc.operation == "select"
    assert "22P02" in exc.hint
    assert exc.likely_rls is False  # not an RLS-class error code


def test_run_select_flags_rls_error_codes():
    query = _FakeQuery(raises=_api_error("42501", "permission denied"))
    with pytest.raises(RepositoryError) as excinfo:
        run_select(query, table="widgets", hint="listing widgets")
    assert excinfo.value.likely_rls is True


# ---------------------------------------------------------------------------
# run_insert
# ---------------------------------------------------------------------------
def test_run_insert_returns_first_row_on_success():
    row = run_insert(_FakeQuery(data=[{"id": "a"}, {"id": "b"}]), table="widgets", hint="creating a widget")
    assert row == {"id": "a"}


def test_run_insert_raises_on_empty_rows_never_a_bare_index_error():
    # The exact bug this task fixes: PostgREST returns 2xx with zero rows
    # (RLS silently filtered the just-written row back out) — must raise a
    # typed, diagnosable RepositoryError, never an unguarded IndexError.
    with pytest.raises(RepositoryError) as excinfo:
        run_insert(_FakeQuery(data=[]), table="session_test_selection", hint="adding a selection row")
    exc = excinfo.value
    assert exc.table == "session_test_selection"
    assert exc.operation == "insert"
    assert exc.likely_rls is True  # zero-rows-on-insert is always treated as a likely RLS rejection
    assert "zero rows" in exc.hint


def test_run_insert_wraps_api_error_from_rejected_write_operation():
    query = _FakeQuery(raises=_api_error("42501", "new row violates row-level security policy"))
    with pytest.raises(RepositoryError) as excinfo:
        run_insert(query, table="test_sessions", hint="creating a session")
    exc = excinfo.value
    assert exc.operation == "insert"
    assert exc.likely_rls is True
    assert "42501" in exc.hint


def test_run_insert_non_rls_api_error_is_not_flagged_likely_rls():
    query = _FakeQuery(raises=_api_error("23502", "null value in column violates not-null constraint"))
    with pytest.raises(RepositoryError) as excinfo:
        run_insert(query, table="test_sessions", hint="creating a session")
    assert excinfo.value.likely_rls is False


def test_repository_error_str_names_table_and_hint():
    exc = RepositoryError(table="instruments", operation="insert", hint="something specific")
    assert "instruments" in str(exc)
    assert "insert" in str(exc)
    assert "something specific" in str(exc)


# ---------------------------------------------------------------------------
# run_update — same two-failure-shape translation as run_insert, but a zero-
# row UPDATE result means the row's CURRENT state didn't satisfy the
# policy's USING clause (session lifecycle transitions, app/routers/sessions.py).
# ---------------------------------------------------------------------------
def test_run_update_returns_first_row_on_success():
    row = run_update(_FakeQuery(data=[{"id": "a", "status": "submitted"}]), table="test_sessions", hint="submitting")
    assert row == {"id": "a", "status": "submitted"}


def test_run_update_raises_on_empty_rows_never_a_bare_index_error():
    with pytest.raises(RepositoryError) as excinfo:
        run_update(_FakeQuery(data=[]), table="test_sessions", hint="approving session 'sess-1'")
    exc = excinfo.value
    assert exc.table == "test_sessions"
    assert exc.operation == "update"
    assert exc.likely_rls is True  # zero-rows-on-update is always treated as a likely RLS rejection
    assert "zero rows" in exc.hint


def test_run_update_wraps_api_error_from_rejected_write():
    query = _FakeQuery(raises=_api_error("42501", "new row violates row-level security policy"))
    with pytest.raises(RepositoryError) as excinfo:
        run_update(query, table="test_sessions", hint="approving session 'sess-1'")
    exc = excinfo.value
    assert exc.operation == "update"
    assert exc.likely_rls is True
    assert "42501" in exc.hint


def test_run_update_non_rls_api_error_is_not_flagged_likely_rls():
    query = _FakeQuery(raises=_api_error("23502", "null value in column violates not-null constraint"))
    with pytest.raises(RepositoryError) as excinfo:
        run_update(query, table="test_sessions", hint="issuing session 'sess-1'")
    assert excinfo.value.likely_rls is False


# ---------------------------------------------------------------------------
# run_rpc — used for issue_certificate_number() (ADR-0008). A Postgres
# function that itself raises surfaces as an APIError exactly like a
# rejected table operation.
# ---------------------------------------------------------------------------
def test_run_rpc_returns_scalar_data_on_success():
    value = run_rpc(_FakeQuery(data="SC-2026-000001"), table="certificate_number_seq", hint="issuing a certificate number")
    assert value == "SC-2026-000001"


def test_run_rpc_raises_on_empty_data():
    with pytest.raises(RepositoryError) as excinfo:
        run_rpc(_FakeQuery(data=None), table="certificate_number_seq", hint="issuing a certificate number")
    assert excinfo.value.operation == "rpc"
    assert excinfo.value.likely_rls is True


def test_run_rpc_wraps_api_error_from_a_raised_postgres_exception():
    # Simulates issue_certificate_number()'s own role-check RAISE EXCEPTION
    # ... USING ERRCODE = '42501' when a non-approver/admin calls it directly.
    query = _FakeQuery(raises=_api_error("42501", "insufficient_privilege: only an approver or admin may issue a certificate number"))
    with pytest.raises(RepositoryError) as excinfo:
        run_rpc(query, table="certificate_number_seq", hint="issuing a certificate number")
    exc = excinfo.value
    assert exc.operation == "rpc"
    assert exc.likely_rls is True
    assert "42501" in exc.hint
