"""Router-level tests for the zero/tare device accuracy endpoints — DB layer
entirely mocked, same pattern as test_sessions_router.py's Weighing tests.
"""

from decimal import Decimal as D

import app.repositories.instruments as instruments_repo
import app.repositories.readings as readings_repo
import app.repositories.sessions as sessions_repo
from app.deps import AuthContext, get_auth_context
from app.main import app
from app.repositories.errors import RepositoryError
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
    "e_value": 1.0,
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

_VALID_BODY = {"sequence_no": 1, "I": "10.4", "delta_l": "0.5", "E0": "0"}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_get_checks_returns_three_checks_starting_at_zero(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    resp = client.get("/api/sessions/sess-1/zero-tare/checks")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert body[0]["sequence_no"] == 0
    assert body[0]["L"] == "0"
    # min_capacity=10.0 (float from PostgREST -> Decimal("10.0")) -> checks
    # are [0, 10.0, 20.0].
    assert body[1]["L"] == "10.0"
    assert body[2]["L"] == "20.0"


def test_get_checks_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.get("/api/sessions/does-not-exist/zero-tare/checks")
    assert resp.status_code == 404


def test_submit_reading_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post("/api/sessions/does-not-exist/zero-tare/readings", json=_VALID_BODY)
    assert resp.status_code == 404


def test_submit_reading_409_when_session_not_draft(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/zero-tare/readings", json=_VALID_BODY)
    assert resp.status_code == 409


def test_submit_reading_rejects_out_of_range_sequence_no(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    resp = client.post("/api/sessions/sess-1/zero-tare/readings", json=dict(_VALID_BODY, sequence_no=99))
    assert resp.status_code == 422


def test_submit_reading_happy_path_writes_reading_and_result_with_null_direction(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    inserted_readings, inserted_results = [], []

    def fake_insert_reading(client, **kwargs):
        inserted_readings.append(kwargs)
        return {"id": "reading-1", **kwargs}

    def fake_insert_result(client, **kwargs):
        inserted_results.append(kwargs)
        return {"id": "result-1", **kwargs}

    monkeypatch.setattr(readings_repo, "insert_reading", fake_insert_reading)
    monkeypatch.setattr(readings_repo, "insert_result", fake_insert_result)
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/zero-tare/readings", json=_VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert isinstance(body["mpe"], str)
    assert isinstance(body["passed"], bool)

    assert len(inserted_readings) == 1
    assert inserted_readings[0]["test_type"] == "weighing"
    assert inserted_readings[0]["direction"] is None  # the zero/tare discriminator
    assert inserted_readings[0]["data"]["L"] == "10.0"  # sequence_no=1 -> min_capacity anchor

    assert len(inserted_results) == 1
    assert inserted_results[0]["test_type"] == "weighing"


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/zero-tare/readings", json=_VALID_BODY)
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


def test_list_readings_filters_out_direction_set_rows_and_dedupes_to_latest(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        # A real Weighing-sequence reading — has a direction, must be excluded.
        {"id": "r-seq", "sequence_no": 0, "direction": "up", "data": {"I": "1", "delta_l": "0", "E0": "0"}, "created_at": "t0"},
        # Two zero/tare submissions for the same sequence_no — latest wins.
        {"id": "r-old", "sequence_no": 1, "direction": None, "data": {"I": "10.1", "delta_l": "0", "E0": "0"}, "created_at": "t1"},
        {"id": "r-new", "sequence_no": 1, "direction": None, "data": {"I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-seq", "result": {"E": "1", "Ec": "1", "mpe": "0.5"}, "passed": False},
        {"reading_id": "r-old", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-new", "result": {"E": "0.4", "Ec": "0.4", "mpe": "0.5"}, "passed": True},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/zero-tare/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["sequence_no"] == 1
    assert body[0]["I"] == "10.4"  # the latest (r-new), not r-old
