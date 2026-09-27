"""Router-level tests for the Sensitivity endpoints — DB layer entirely
mocked. Covers the non-self-indicating-only applicability gate and the
tiered pass threshold end to end through the API."""

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

_NSI_INSTRUMENT_ROW = {
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
    "max_capacity": 1000.0,
    "min_capacity": 10.0,
    "indication_type": "non_self_indicating",
    "is_mobile": False,
    "is_multi_interval": False,
    "created_at": "2026-01-01T00:00:00Z",
}

_DIGITAL_INSTRUMENT_ROW = dict(_NSI_INSTRUMENT_ROW, indication_type="digital")

_DRAFT_SESSION_ROW = {
    "id": "sess-1",
    "instrument_id": "instr-1",
    "verification_type": "initial",
    "status": "draft",
    "created_by": _FAKE_AUTH.user_id,
    "created_at": "2026-01-01T00:00:00Z",
}

_VALID_BODY = {"sequence_no": 1, "permanent_displacement_mm": "2.5"}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_get_checks_includes_threshold_mm(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NSI_INSTRUMENT_ROW)

    resp = client.get("/api/sessions/sess-1/sensitivity/checks")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert all(D(check["threshold_mm"]) == D("2") for check in body)  # Class III, Max=1000g


def test_submit_reading_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post("/api/sessions/does-not-exist/sensitivity/readings", json=_VALID_BODY)
    assert resp.status_code == 404


def test_submit_reading_409_when_session_not_draft(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/sensitivity/readings", json=_VALID_BODY)
    assert resp.status_code == 409


def test_submit_reading_rejects_non_non_self_indicating_instrument(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _DIGITAL_INSTRUMENT_ROW)

    resp = client.post("/api/sessions/sess-1/sensitivity/readings", json=_VALID_BODY)
    assert resp.status_code == 422
    assert "non-self-indicating" in resp.json()["detail"]


def test_submit_reading_rejects_out_of_range_sequence_no(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NSI_INSTRUMENT_ROW)

    resp = client.post("/api/sessions/sess-1/sensitivity/readings", json=dict(_VALID_BODY, sequence_no=99))
    assert resp.status_code == 422


def test_submit_reading_happy_path_passes_at_threshold(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NSI_INSTRUMENT_ROW)

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

    resp = client.post("/api/sessions/sess-1/sensitivity/readings", json=_VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert D(body["threshold_mm"]) == D("2")
    assert body["passed"] is True

    assert inserted_readings[0]["test_type"] == "sensitivity"
    assert inserted_readings[0]["data"] == {"permanent_displacement_mm": "2.5"}
    assert inserted_results[0]["passed"] is True


def test_submit_reading_fails_under_threshold(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NSI_INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/sensitivity/readings", json=dict(_VALID_BODY, permanent_displacement_mm="1.9"))
    assert resp.status_code == 201
    assert resp.json()["passed"] is False


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NSI_INSTRUMENT_ROW)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/sensitivity/readings", json=_VALID_BODY)
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


def test_list_readings_dedupes_to_latest_per_sequence_no(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-old", "sequence_no": 1, "data": {"permanent_displacement_mm": "1.0"}, "created_at": "t1"},
        {"id": "r-new", "sequence_no": 1, "data": {"permanent_displacement_mm": "2.5"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-old", "result": {"threshold_mm": "2"}, "passed": False},
        {"reading_id": "r-new", "result": {"threshold_mm": "2"}, "passed": True},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/sensitivity/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["passed"] is True
