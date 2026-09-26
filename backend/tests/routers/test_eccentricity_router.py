"""Router-level tests for the Eccentricity endpoints — DB layer entirely
mocked, same pattern as the other new-test-form router test files.
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
    "max_capacity": 3000.0,
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

_VALID_BODY = {"position_no": 1, "I": "1000.4", "delta_l": "0.5", "E0": "0"}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_get_setup_returns_one_third_of_max_and_its_mpe(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    resp = client.get("/api/sessions/sess-1/eccentricity/setup")
    assert resp.status_code == 200
    body = resp.json()
    assert D(body["L"]) == D("1000")
    assert D(body["mpe"]) == D("1.0")  # m=1000 -> Band 2 for Class III


def test_get_setup_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.get("/api/sessions/does-not-exist/eccentricity/setup")
    assert resp.status_code == 404


def test_submit_reading_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post("/api/sessions/does-not-exist/eccentricity/readings", json=_VALID_BODY)
    assert resp.status_code == 404


def test_submit_reading_409_when_session_not_draft(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/eccentricity/readings", json=_VALID_BODY)
    assert resp.status_code == 409


def test_submit_reading_rejects_bad_position_no():
    resp = client.post("/api/sessions/sess-1/eccentricity/readings", json=dict(_VALID_BODY, position_no=5))
    assert resp.status_code == 422


def test_submit_reading_happy_path_writes_reading_and_result_keyed_by_position(monkeypatch):
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

    resp = client.post("/api/sessions/sess-1/eccentricity/readings", json=_VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert body["position_no"] == 1
    assert isinstance(body["passed"], bool)

    assert len(inserted_readings) == 1
    assert inserted_readings[0]["test_type"] == "eccentricity"
    assert inserted_readings[0]["position_no"] == 1
    assert inserted_readings[0]["sequence_no"] == 1
    assert inserted_readings[0]["data"]["E0"] == "0"

    assert len(inserted_results) == 1
    assert inserted_results[0]["test_type"] == "eccentricity"


def test_submit_reading_different_e0_per_position_produces_different_ec(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp_1 = client.post("/api/sessions/sess-1/eccentricity/readings", json=dict(_VALID_BODY, position_no=1, E0="0"))
    resp_2 = client.post("/api/sessions/sess-1/eccentricity/readings", json=dict(_VALID_BODY, position_no=2, E0="0.3"))

    assert D(resp_1.json()["E"]) == D(resp_2.json()["E"])  # same I/L/delta_l -> same raw E
    assert D(resp_2.json()["Ec"]) == D(resp_1.json()["Ec"]) - D("0.3")


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/eccentricity/readings", json=_VALID_BODY)
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


def test_list_readings_dedupes_to_latest_per_position(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-old", "position_no": 1, "data": {"I": "1000.1", "delta_l": "0", "E0": "0"}, "created_at": "t1"},
        {"id": "r-new", "position_no": 1, "data": {"I": "1000.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-old", "result": {"E": "0.1", "Ec": "0.1", "mpe": "1.0"}, "passed": True},
        {"reading_id": "r-new", "result": {"E": "0.4", "Ec": "0.4", "mpe": "1.0"}, "passed": True},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/eccentricity/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["position_no"] == 1
    assert D(body[0]["I"]) == D("1000.4")
