"""Router-level tests for the Discrimination endpoints — DB layer entirely
mocked. Covers all three sub-procedures (the applicable one derived from
the instrument's own indication_type)."""

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


def _instrument_row(indication_type, **overrides):
    row = {
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
        "max_capacity": 6000.0,
        "min_capacity": 20.0,
        "indication_type": indication_type,
        "is_mobile": False,
        "is_multi_interval": False,
        "created_at": "2026-01-01T00:00:00Z",
    }
    row.update(overrides)
    return row


_ANALOG_ROW = _instrument_row("analog")
_NSI_ROW = _instrument_row("non_self_indicating")
_DIGITAL_ROW = _instrument_row("digital")

_DRAFT_SESSION_ROW = {
    "id": "sess-1",
    "instrument_id": "instr-1",
    "verification_type": "initial",
    "status": "draft",
    "created_by": _FAKE_AUTH.user_id,
    "created_at": "2026-01-01T00:00:00Z",
}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_get_checks_has_no_mpe_for_digital_instrument(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _DIGITAL_ROW)

    resp = client.get("/api/sessions/sess-1/discrimination/checks")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert all(check["mpe"] is None for check in body)
    assert all(check["variant"] == "digital" for check in body)


def test_get_checks_has_mpe_for_analog_instrument(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _ANALOG_ROW)

    resp = client.get("/api/sessions/sess-1/discrimination/checks")
    assert resp.status_code == 200
    body = resp.json()
    assert all(check["mpe"] is not None for check in body)
    assert all(check["variant"] == "analog" for check in body)


def test_submit_reading_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post("/api/sessions/does-not-exist/discrimination/readings", json={"sequence_no": 0, "I1": "1", "I2": "2"})
    assert resp.status_code == 404


def test_submit_reading_409_when_session_not_draft(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/discrimination/readings", json={"sequence_no": 0, "I1": "1", "I2": "2"})
    assert resp.status_code == 409


def test_submit_reading_analog_missing_i1_i2_is_422(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _ANALOG_ROW)

    resp = client.post("/api/sessions/sess-1/discrimination/readings", json={"sequence_no": 0})
    assert resp.status_code == 422


def test_submit_reading_analog_happy_path(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _ANALOG_ROW)

    inserted_readings, inserted_results = [], []

    def fake_insert_reading(client, **kwargs):
        inserted_readings.append(kwargs)
        return {"id": "r-1", **kwargs}

    def fake_insert_result(client, **kwargs):
        inserted_results.append(kwargs)
        return {"id": "res-1", **kwargs}

    monkeypatch.setattr(readings_repo, "insert_reading", fake_insert_reading)
    monkeypatch.setattr(readings_repo, "insert_result", fake_insert_result)
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/discrimination/readings", json={"sequence_no": 0, "I1": "20", "I2": "21"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["variant"] == "analog"
    assert D(body["difference"]) == D("1")

    assert inserted_readings[0]["test_type"] == "discrimination"
    assert inserted_readings[0]["data"] == {"I1": "20", "I2": "21"}
    assert inserted_results[0]["test_type"] == "discrimination"


def test_submit_reading_non_self_indicating_qualitative_pass(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NSI_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kw: {"id": "r-1", **kw})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kw: {"id": "res-1", **kw})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/discrimination/readings", json={"sequence_no": 0, "visible_displacement": True})
    assert resp.status_code == 201
    body = resp.json()
    assert body["variant"] == "non_self_indicating"
    assert body["passed"] is True

    resp_fail = client.post("/api/sessions/sess-1/discrimination/readings", json={"sequence_no": 1, "visible_displacement": False})
    assert resp_fail.json()["passed"] is False


def test_submit_reading_digital_happy_path_no_mpe(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _DIGITAL_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kw: {"id": "r-1", **kw})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kw: {"id": "res-1", **kw})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/discrimination/readings", json={"sequence_no": 0, "I1": "20", "I2": "21"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["variant"] == "digital"
    assert body["mpe"] is None
    assert D(body["d"]) == D("1")  # falls back to e_value (1.0)
    assert body["passed"] is True


def test_submit_reading_rejects_out_of_range_sequence_no(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _ANALOG_ROW)

    resp = client.post("/api/sessions/sess-1/discrimination/readings", json={"sequence_no": 99, "I1": "1", "I2": "2"})
    assert resp.status_code == 422


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _ANALOG_ROW)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/discrimination/readings", json={"sequence_no": 0, "I1": "1", "I2": "2"})
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


def test_list_readings_dedupes_to_latest_per_sequence_no(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-old", "sequence_no": 0, "data": {"visible_displacement": False}, "created_at": "t1"},
        {"id": "r-new", "sequence_no": 0, "data": {"visible_displacement": True}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-old", "result": {"variant": "non_self_indicating"}, "passed": False},
        {"reading_id": "r-new", "result": {"variant": "non_self_indicating"}, "passed": True},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/discrimination/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["passed"] is True
