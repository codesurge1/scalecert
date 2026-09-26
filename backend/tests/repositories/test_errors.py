"""Pure unit tests for app.repositories.errors — no DB, no HTTP. Proves
`run_select`/`run_insert` never let a bare `IndexError` or unhandled
`postgrest.exceptions.APIError` escape, for both failure shapes CLAUDE.md
calls out: an explicit PostgREST error, and a "successful" empty result.
"""

import pytest
from postgrest.exceptions import APIError

from app.repositories.errors import RepositoryError, run_insert, run_select


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
