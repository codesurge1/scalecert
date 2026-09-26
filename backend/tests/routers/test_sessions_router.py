"""Router-level tests: the DB layer is entirely mocked (monkeypatched
repository functions, no live Supabase). Verifies not-found -> 404,
not-draft -> 409, out-of-range sequence_no -> 422, the happy path writing
reading+result together, the orphan-reading rollback on result-insert
failure, that an audit-log failure is non-fatal, and — the previously
untested path — POST /sessions (create_session): the happy path, malformed
instrument_id -> 422, instrument not found -> 404, and that a
RepositoryError from either insert step maps to a clean, informative 403/500
rather than the bare IndexError-triggered 500 this task fixes.
"""

import app.repositories.instruments as instruments_repo
import app.repositories.readings as readings_repo
import app.repositories.sessions as sessions_repo
from app.deps import AuthContext, get_auth_context
from app.main import app
from app.repositories.errors import RepositoryError
from fastapi.testclient import TestClient

client = TestClient(app)

_FAKE_AUTH = AuthContext(client=object(), user_id="11111111-1111-1111-1111-111111111111", token="tok")
_INSTRUMENT_ID = "11111111-1111-4111-8111-111111111111"

_INSTRUMENT_ROW = {
    "id": "instr-1",
    "registered_by": _FAKE_AUTH.user_id,
    "application_no": None,
    "type_designation": None,
    "manufacturer": None,
    "model": None,
    "serial_number": None,
    "accuracy_class": "III",
    "e_value": 1.0,  # float, as PostgREST actually returns a `numeric` column
    "d_value": None,
    "max_capacity": 5000.0,
    "min_capacity": 10.0,
    "indication_type": "digital",
    "is_mobile": False,
    "is_multi_interval": False,
    "created_at": "2026-01-01T00:00:00Z",
}

_DRAFT_SESSION_ROW = {
    "id": "sess-1",
    "instrument_id": "instr-1",
    "verification_type": "initial",
    "status": "draft",
    "created_by": _FAKE_AUTH.user_id,
    "created_at": "2026-01-01T00:00:00Z",
}

_VALID_READING_BODY = {"sequence_no": 0, "direction": "up", "I": "300.4", "delta_l": "0.5", "E0": "0"}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_create_session_happy_path(monkeypatch):
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(sessions_repo, "insert_session", lambda client, created_by, payload: dict(_DRAFT_SESSION_ROW))
    monkeypatch.setattr(
        sessions_repo,
        "insert_session_test_selection",
        lambda client, session_id, test_type: {"id": "sel-1", "session_id": session_id, "test_type": test_type},
    )
    monkeypatch.setattr(
        sessions_repo,
        "get_session_test_selections",
        lambda client, session_id: [
            {
                "id": "sel-1",
                "session_id": session_id,
                "test_type": "weighing",
                "applicable": True,
                "na_reason": None,
                "zero_device_status": None,
                "status": "pending",
            }
        ],
    )

    resp = client.post("/api/sessions", json={"instrument_id": _INSTRUMENT_ID, "verification_type": "initial"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft"
    assert body["test_selections"][0]["test_type"] == "weighing"


def test_create_session_404_when_instrument_not_found(monkeypatch):
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: None)
    resp = client.post("/api/sessions", json={"instrument_id": _INSTRUMENT_ID, "verification_type": "initial"})
    assert resp.status_code == 404


def test_create_session_422_when_instrument_id_malformed():
    # The exact frontend-bug shape (empty/"undefined"/non-UUID) that used to
    # reach Postgres and 500 — now a clean 422 before any DB call, so no repo
    # mocking is needed here at all.
    resp = client.post("/api/sessions", json={"instrument_id": "not-a-uuid", "verification_type": "initial"})
    assert resp.status_code == 422


def test_create_session_maps_likely_rls_repository_error_to_403(monkeypatch):
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    def failing_insert_session(client, created_by, payload):
        raise RepositoryError(
            table="test_sessions", operation="insert", hint="RLS rejected it", likely_rls=True
        )

    monkeypatch.setattr(sessions_repo, "insert_session", failing_insert_session)

    resp = client.post("/api/sessions", json={"instrument_id": _INSTRUMENT_ID, "verification_type": "initial"})
    assert resp.status_code == 403
    assert "test_sessions" in resp.json()["detail"]


def test_create_session_maps_non_rls_repository_error_to_500(monkeypatch):
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    def failing_insert_session(client, created_by, payload):
        raise RepositoryError(table="test_sessions", operation="insert", hint="something else broke", likely_rls=False)

    monkeypatch.setattr(sessions_repo, "insert_session", failing_insert_session)

    resp = client.post("/api/sessions", json={"instrument_id": _INSTRUMENT_ID, "verification_type": "initial"})
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "something else broke" in detail  # never a bare, undiagnosable "Internal Server Error"


def test_create_session_maps_repository_error_from_second_insert_step(monkeypatch):
    # insert_session succeeds; insert_session_test_selection (the second
    # step — the more RLS-exposed one, see repositories/sessions.py) fails.
    # This is exactly the two-step-insert scenario the prior diagnosis named.
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(sessions_repo, "insert_session", lambda client, created_by, payload: dict(_DRAFT_SESSION_ROW))

    def failing_insert_selection(client, session_id, test_type):
        raise RepositoryError(
            table="session_test_selection",
            operation="insert",
            hint="insert returned zero rows; likely an RLS policy silently rejected it",
            likely_rls=True,
        )

    monkeypatch.setattr(sessions_repo, "insert_session_test_selection", failing_insert_selection)

    resp = client.post("/api/sessions", json={"instrument_id": _INSTRUMENT_ID, "verification_type": "initial"})
    assert resp.status_code == 403
    assert "session_test_selection" in resp.json()["detail"]


def test_get_session_404_when_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.get("/api/sessions/does-not-exist")
    assert resp.status_code == 404


def test_get_session_404_not_500_when_id_is_malformed(monkeypatch):
    # Simulates what repositories.sessions.get_session now raises (via
    # run_select) for a path param that isn't a valid UUID — Postgres's
    # "invalid input syntax for type uuid". Before this task's fix, nothing
    # caught this and it fell through as an unhandled 500 with no detail;
    # it now folds into the same clean 404 a genuinely missing session gets.
    def raise_malformed_id(client, session_id):
        raise RepositoryError(
            table="test_sessions",
            operation="select",
            hint="PostgREST error 22P02: invalid input syntax for type uuid",
            likely_rls=False,
        )

    monkeypatch.setattr(sessions_repo, "get_session", raise_malformed_id)
    resp = client.get("/api/sessions/not-a-uuid")
    assert resp.status_code == 404
    assert "22P02" in resp.json()["detail"]


def test_get_session_returns_selections(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(
        sessions_repo,
        "get_session_test_selections",
        lambda client, session_id: [
            {
                "id": "sel-1",
                "session_id": session_id,
                "test_type": "weighing",
                "applicable": True,
                "na_reason": None,
                "zero_device_status": None,
                "status": "pending",
            }
        ],
    )
    resp = client.get("/api/sessions/sess-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "draft"
    assert body["test_selections"][0]["test_type"] == "weighing"


def test_get_weighing_sequence_returns_entries(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    resp = client.get("/api/sessions/sess-1/weighing/sequence")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 5
    assert body[0]["sequence_no"] == 0
    assert all(isinstance(entry["L"], str) for entry in body)  # never a JSON number


def test_get_weighing_sequence_404_when_session_not_visible(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.get("/api/sessions/sess-1/weighing/sequence")
    assert resp.status_code == 404


def _reading_row(row_id, sequence_no, direction, created_at, *, I="300.4", delta_l="0.5", E0="0"):
    return {
        "id": row_id,
        "session_id": "sess-1",
        "test_type": "weighing",
        "sequence_no": sequence_no,
        "direction": direction,
        "data": {
            "accuracy_class": "III",
            "verification_type": "initial",
            "direction": direction,
            "e": "1",
            "L": "10",
            "I": I,
            "delta_l": delta_l,
            "E0": E0,
        },
        "entered_by": _FAKE_AUTH.user_id,
        "created_at": created_at,
    }


def _result_row(row_id, reading_id, *, E="0.4", Ec="0.4", mpe="0.5", passed=True):
    return {
        "id": row_id,
        "session_id": "sess-1",
        "test_type": "weighing",
        "reading_id": reading_id,
        "result": {
            "accuracy_class": "III",
            "verification_type": "initial",
            "L": "10",
            "I": "300.4",
            "delta_l": "0.5",
            "E0": "0",
            "E": E,
            "Ec": Ec,
            "mpe": mpe,
            "margin": "0.1",
            "passed": passed,
            "mpe_in_e": "0.5",
            "band_lower_m": "0",
            "band_upper_m": "500",
        },
        "passed": passed,
        "computed_at": "2026-01-01T00:00:00Z",
    }


def test_list_weighing_readings_returns_paired_records(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(
        readings_repo,
        "list_readings",
        lambda client, **kwargs: [
            _reading_row("r-up", 0, "up", "2026-01-01T00:00:00Z"),
            _reading_row("r-down", 0, "down", "2026-01-01T00:00:01Z"),
        ],
    )
    monkeypatch.setattr(
        readings_repo,
        "list_results",
        lambda client, **kwargs: [
            _result_row("res-up", "r-up"),
            _result_row("res-down", "r-down"),
        ],
    )

    resp = client.get("/api/sessions/sess-1/weighing/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert {record["direction"] for record in body} == {"up", "down"}
    assert all(record["sequence_no"] == 0 for record in body)
    assert all(isinstance(record["E"], str) for record in body)  # never a JSON number


def test_list_weighing_readings_dedupes_to_latest_per_sequence_and_direction(monkeypatch):
    # Two "up" readings at sequence_no 0 (no update endpoint exists — a
    # resubmission is a second insert). Only the later one (by created_at)
    # should survive into the response.
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(
        readings_repo,
        "list_readings",
        lambda client, **kwargs: [
            _reading_row("r-old", 0, "up", "2026-01-01T00:00:00Z", I="300.4"),
            _reading_row("r-new", 0, "up", "2026-01-01T00:00:05Z", I="300.6"),
        ],
    )
    monkeypatch.setattr(
        readings_repo,
        "list_results",
        lambda client, **kwargs: [
            _result_row("res-old", "r-old", E="0.4", Ec="0.4"),
            _result_row("res-new", "r-new", E="0.6", Ec="0.6", passed=False),
        ],
    )

    resp = client.get("/api/sessions/sess-1/weighing/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["I"] == "300.6"
    assert body[0]["passed"] is False


def test_list_weighing_readings_skips_readings_with_no_matching_result(monkeypatch):
    # Defensive: the reading+result rollback (see submit_weighing_reading)
    # should make this impossible in practice, but an orphan reading must
    # never crash the endpoint or be silently invented a fake result.
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(
        readings_repo, "list_readings", lambda client, **kwargs: [_reading_row("r-orphan", 0, "up", "2026-01-01T00:00:00Z")]
    )
    monkeypatch.setattr(readings_repo, "list_results", lambda client, **kwargs: [])

    resp = client.get("/api/sessions/sess-1/weighing/readings")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_weighing_readings_404_when_session_not_visible(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.get("/api/sessions/sess-1/weighing/readings")
    assert resp.status_code == 404


def test_submit_reading_rejects_when_not_draft(monkeypatch):
    monkeypatch.setattr(
        sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted")
    )
    resp = client.post("/api/sessions/sess-1/weighing/readings", json=_VALID_READING_BODY)
    assert resp.status_code == 409


def test_submit_reading_rejects_out_of_range_sequence_no(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    resp = client.post(
        "/api/sessions/sess-1/weighing/readings",
        json=dict(_VALID_READING_BODY, sequence_no=9999),
    )
    assert resp.status_code == 422


def test_submit_reading_happy_path_writes_reading_and_result(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    inserted_readings, inserted_results, audit_calls = [], [], []

    def fake_insert_reading(client, **kwargs):
        inserted_readings.append(kwargs)
        return {"id": "reading-1", **kwargs}

    def fake_insert_result(client, **kwargs):
        inserted_results.append(kwargs)
        return {"id": "result-1", **kwargs}

    def fake_insert_audit_log(client, **kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(readings_repo, "insert_reading", fake_insert_reading)
    monkeypatch.setattr(readings_repo, "insert_result", fake_insert_result)
    monkeypatch.setattr(readings_repo, "insert_audit_log", fake_insert_audit_log)

    resp = client.post("/api/sessions/sess-1/weighing/readings", json=_VALID_READING_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert isinstance(body["mpe"], str)
    assert isinstance(body["passed"], bool)

    assert len(inserted_readings) == 1
    assert len(inserted_results) == 1
    assert len(audit_calls) == 1
    assert inserted_readings[0]["entered_by"] == _FAKE_AUTH.user_id
    assert inserted_readings[0]["data"]["L"] == inserted_readings[0]["data"]["L"]  # present, string-valued
    assert isinstance(inserted_readings[0]["data"]["L"], str)


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RuntimeError("simulated DB failure")

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/weighing/readings", json=_VALID_READING_BODY)
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


def test_submit_reading_succeeds_even_if_audit_log_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-1", **kwargs})

    def failing_audit(client, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(readings_repo, "insert_audit_log", failing_audit)

    resp = client.post("/api/sessions/sess-1/weighing/readings", json=_VALID_READING_BODY)
    assert resp.status_code == 201  # audit failure must not fail the request
