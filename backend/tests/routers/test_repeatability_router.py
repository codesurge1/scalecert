"""Router-level tests for the Repeatability endpoints — DB layer entirely
mocked. Uses Max=1000g (not the shared 5000g fixture other router test files
use) specifically so series 1 (L=500, m=500) and series 2 (L=1000, m=1000)
land in different Table 6 bands (mpe=0.5g vs 1.0g) — proving "each series has
its own mpe" end to end through the API, not just in the engine/service
layers already covered elsewhere.
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
    "max_capacity": 1000.0,
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

_VALID_BODY = {"series_no": 1, "sequence_no": 0, "I": "500.1", "delta_l": "0.5"}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_list_readings_returns_two_not_started_series_with_correct_distinct_mpe(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: [])

    resp = client.get("/api/sessions/sess-1/repeatability/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["series_no"] == 1
    assert D(body[0]["L"]) == D("500")
    assert D(body[0]["mpe"]) == D("0.5")
    assert body[0]["readings"] == []
    assert body[0]["passed"] is None

    assert body[1]["series_no"] == 2
    assert D(body[1]["L"]) == D("1000")
    assert D(body[1]["mpe"]) == D("1.0")


def test_list_readings_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.get("/api/sessions/does-not-exist/repeatability/readings")
    assert resp.status_code == 404


def test_submit_reading_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post("/api/sessions/does-not-exist/repeatability/readings", json=_VALID_BODY)
    assert resp.status_code == 404


def test_submit_reading_409_when_session_not_draft(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/repeatability/readings", json=_VALID_BODY)
    assert resp.status_code == 409


def test_submit_reading_rejects_bad_series_no():
    resp = client.post("/api/sessions/sess-1/repeatability/readings", json=dict(_VALID_BODY, series_no=3))
    assert resp.status_code == 422


def test_submit_reading_rejects_bad_sequence_no():
    resp = client.post("/api/sessions/sess-1/repeatability/readings", json=dict(_VALID_BODY, sequence_no=10))
    assert resp.status_code == 422


def test_submit_reading_happy_path_writes_reading_and_series_level_result(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
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

    resp = client.post("/api/sessions/sess-1/repeatability/readings", json=_VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert body["series_no"] == 1
    assert len(body["readings"]) == 1
    assert D(body["readings"][0]["E"]) == D("0.1")
    assert body["passed"] is True

    assert len(inserted_readings) == 1
    assert inserted_readings[0]["test_type"] == "repeatability"
    assert inserted_readings[0]["series_no"] == 1
    assert inserted_readings[0]["sequence_no"] == 0
    assert inserted_readings[0]["data"] == {"I": "500.1", "delta_l": "0.5"}

    assert len(inserted_results) == 1
    assert inserted_results[0]["test_type"] == "repeatability"
    assert inserted_results[0]["passed"] is True


def test_submit_reading_series_out_reflects_previously_stored_readings_too(monkeypatch):
    # A prior reading (sequence_no=1) is already stored — the response after
    # submitting sequence_no=0 must include BOTH, proving the series is
    # recomputed from the full stored set, not just the new submission.
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(
        readings_repo,
        "list_readings",
        lambda client, session_id, test_type: [
            {"id": "r-1", "series_no": 1, "sequence_no": 1, "data": {"I": "500.2", "delta_l": "0.5"}, "created_at": "t0"}
        ],
    )
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-2", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-2", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/repeatability/readings", json=_VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["readings"]) == 2
    assert {r["sequence_no"] for r in body["readings"]} == {0, 1}
    assert D(body["spread"]) == D("0.1")


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: [])

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/repeatability/readings", json=_VALID_BODY)
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]
