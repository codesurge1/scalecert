"""Router-level tests for the Voltage variations endpoints — DB layer
entirely mocked, same pattern as test_zero_tare_router.py (the closest
analog: computed via the Weighing engine at a small fixed load)."""

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

_NSI_INSTRUMENT_ROW = dict(_INSTRUMENT_ROW, indication_type="non_self_indicating")

_DRAFT_SESSION_ROW = {
    "id": "sess-1",
    "instrument_id": "instr-1",
    "verification_type": "initial",
    "status": "draft",
    "created_by": _FAKE_AUTH.user_id,
    "created_at": "2026-01-01T00:00:00Z",
}

_VALID_BODY = {"level_key": "reference", "U": "230", "I": "10.4", "delta_l": "0.5", "E0": "0"}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_get_levels_returns_three_levels_at_10e(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    resp = client.get("/api/sessions/sess-1/voltage-variations/levels")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert all(level["L"] == "10.0" for level in body)
    assert {level["level_key"] for level in body} == {"reference", "lower", "upper"}


def test_submit_reading_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post("/api/sessions/does-not-exist/voltage-variations/readings", json=_VALID_BODY)
    assert resp.status_code == 404


def test_submit_reading_409_when_session_not_draft(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/voltage-variations/readings", json=_VALID_BODY)
    assert resp.status_code == 409


def test_submit_reading_rejects_non_self_indicating_instrument(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NSI_INSTRUMENT_ROW)

    resp = client.post("/api/sessions/sess-1/voltage-variations/readings", json=_VALID_BODY)
    assert resp.status_code == 422
    assert "electronic" in resp.json()["detail"]


def test_submit_reading_rejects_bad_level_key(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    resp = client.post("/api/sessions/sess-1/voltage-variations/readings", json=dict(_VALID_BODY, level_key="nominal"))
    assert resp.status_code == 422


def test_submit_reading_happy_path_writes_reading_and_result(monkeypatch):
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

    resp = client.post("/api/sessions/sess-1/voltage-variations/readings", json=_VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert body["level_key"] == "reference"
    assert body["U"] == "230"
    assert isinstance(body["passed"], bool)

    assert inserted_readings[0]["test_type"] == "voltage_variations"
    assert inserted_readings[0]["sequence_no"] == 0  # reference -> index 0
    assert inserted_readings[0]["data"]["level_key"] == "reference"
    assert inserted_results[0]["test_type"] == "voltage_variations"


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/voltage-variations/readings", json=_VALID_BODY)
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


def test_list_readings_dedupes_to_latest_per_level(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-old", "sequence_no": 0, "data": {"level_key": "reference", "U": "230", "I": "10.1", "delta_l": "0", "E0": "0"}, "created_at": "t1"},
        {"id": "r-new", "sequence_no": 0, "data": {"level_key": "reference", "U": "230", "I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-old", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-new", "result": {"E": "0.4", "Ec": "0.4", "mpe": "0.5"}, "passed": True},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/voltage-variations/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["I"] == "10.4"  # the latest (r-new)
