"""Router-level tests for the Tilting endpoints — DB layer entirely mocked.
Covers the mobile-only applicability gate and that the POST response
reflects the WHOLE recomputed state (not just the one submitted reading),
same pattern as Repeatability's router tests.
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

_MOBILE_INSTRUMENT_ROW = {
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
    "indication_type": "digital",
    "is_mobile": True,
    "is_multi_interval": False,
    "created_at": "2026-01-01T00:00:00Z",
}

_NON_MOBILE_INSTRUMENT_ROW = dict(_MOBILE_INSTRUMENT_ROW, is_mobile=False)

_DRAFT_SESSION_ROW = {
    "id": "sess-1",
    "instrument_id": "instr-1",
    "verification_type": "initial",
    "status": "draft",
    "created_by": _FAKE_AUTH.user_id,
    "created_at": "2026-01-01T00:00:00Z",
}

_VALID_BODY = {"phase": "unloaded", "position_no": 1, "I": "100.5", "delta_l": "0.5"}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_get_state_with_no_readings_still_knows_l_and_mpe(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _MOBILE_INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: [])

    resp = client.get("/api/sessions/sess-1/tilting/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert D(body["L"]) == D("500")
    assert D(body["mpe_l"]) == D("0.5")
    assert D(body["mpe_max"]) == D("1.0")
    assert body["readings"] == []
    assert body["passed"] is None


def test_get_state_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.get("/api/sessions/does-not-exist/tilting/readings")
    assert resp.status_code == 404


def test_submit_reading_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post("/api/sessions/does-not-exist/tilting/readings", json=_VALID_BODY)
    assert resp.status_code == 404


def test_submit_reading_409_when_session_not_draft(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/tilting/readings", json=_VALID_BODY)
    assert resp.status_code == 409


def test_submit_reading_rejects_non_mobile_instrument(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NON_MOBILE_INSTRUMENT_ROW)

    resp = client.post("/api/sessions/sess-1/tilting/readings", json=_VALID_BODY)
    assert resp.status_code == 422
    assert "mobile" in resp.json()["detail"]


def test_submit_reading_rejects_bad_phase():
    resp = client.post("/api/sessions/sess-1/tilting/readings", json=dict(_VALID_BODY, phase="sideways"))
    assert resp.status_code == 422


def test_submit_reading_rejects_bad_position_no():
    resp = client.post("/api/sessions/sess-1/tilting/readings", json=dict(_VALID_BODY, position_no=6))
    assert resp.status_code == 422


def test_submit_unloaded_reading_happy_path_encodes_phase_as_sequence_no(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _MOBILE_INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: [])

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

    resp = client.post("/api/sessions/sess-1/tilting/readings", json=_VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["readings"]) == 1
    assert body["readings"][0]["phase"] == "unloaded"
    assert body["readings"][0]["position_no"] == 1
    assert D(body["readings"][0]["E"]) == D("100.5")

    assert inserted_readings[0]["test_type"] == "tilting"
    assert inserted_readings[0]["sequence_no"] == 0  # "unloaded" encoded as 0
    assert inserted_readings[0]["position_no"] == 1


def test_submit_reading_response_reflects_previously_stored_readings_too(monkeypatch):
    # A prior unloaded reading for position 1 is already stored; submitting
    # position 1's loaded_l reading must produce a response with BOTH,
    # including a real Ec (not None) — proving the whole state is
    # recomputed, not just the new reading in isolation.
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _MOBILE_INSTRUMENT_ROW)
    monkeypatch.setattr(
        readings_repo,
        "list_readings",
        lambda client, session_id, test_type: [
            {"id": "r-1", "sequence_no": 0, "position_no": 1, "data": {"I": "100.5", "delta_l": "0.5"}, "created_at": "t0"}
        ],
    )
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-2", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-2", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post(
        "/api/sessions/sess-1/tilting/readings",
        json={"phase": "loaded_l", "position_no": 1, "I": "600.7", "delta_l": "0.5"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["readings"]) == 2
    loaded_row = next(r for r in body["readings"] if r["phase"] == "loaded_l")
    assert D(loaded_row["Ec"]) == D("0.2")  # E=100.7, E0=100.5 -> Ec=0.2


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _MOBILE_INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: [])

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/tilting/readings", json=_VALID_BODY)
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]
