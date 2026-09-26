"""Router-level tests: the DB layer is entirely mocked (monkeypatched
repository functions, no live Supabase). Verifies not-found -> 404,
not-draft -> 409, out-of-range sequence_no -> 422, the happy path writing
reading+result together, the orphan-reading rollback on result-insert
failure, and that an audit-log failure is non-fatal.
"""

import app.repositories.instruments as instruments_repo
import app.repositories.readings as readings_repo
import app.repositories.sessions as sessions_repo
from app.deps import AuthContext, get_auth_context
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

_FAKE_AUTH = AuthContext(client=object(), user_id="11111111-1111-1111-1111-111111111111", token="tok")

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


def test_get_session_404_when_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.get("/api/sessions/does-not-exist")
    assert resp.status_code == 404


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
