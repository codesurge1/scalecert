"""Router-level tests for the record-only clause-12.x disturbance endpoints
— DB layer entirely mocked. Exercises the shared implementation primarily
through the /ac-mains-dips path (the simplest condition list, no `group`),
plus one smoke test per other registered test (/electrical-bursts,
/electrostatic-discharges) to confirm each is wired to its own condition
list and test_type."""

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


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_get_conditions_returns_the_fixed_list(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    resp = client.get("/api/sessions/sess-1/ac-mains-dips/conditions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 7
    assert body[0]["condition_key"] == "baseline"


def test_submit_reading_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post(
        "/api/sessions/does-not-exist/ac-mains-dips/readings",
        json={"condition_key": "dip_0pct_1cycle", "indication": "1000", "significant_fault": False},
    )
    assert resp.status_code == 404


def test_submit_reading_409_when_session_not_draft(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post(
        "/api/sessions/sess-1/ac-mains-dips/readings",
        json={"condition_key": "dip_0pct_1cycle", "indication": "1000", "significant_fault": False},
    )
    assert resp.status_code == 409


def test_submit_reading_rejects_non_self_indicating_instrument(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _NSI_INSTRUMENT_ROW)

    resp = client.post(
        "/api/sessions/sess-1/ac-mains-dips/readings",
        json={"condition_key": "dip_0pct_1cycle", "indication": "1000", "significant_fault": False},
    )
    assert resp.status_code == 422
    assert "electronic" in resp.json()["detail"]


def test_submit_reading_rejects_unknown_condition_key(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    resp = client.post(
        "/api/sessions/sess-1/ac-mains-dips/readings",
        json={"condition_key": "not-a-real-condition", "indication": "1000", "significant_fault": False},
    )
    assert resp.status_code == 422


def test_submit_reading_happy_path_no_fault_passes(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    inserted_readings, inserted_results = [], []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: (inserted_readings.append(kwargs), {"id": "reading-1", **kwargs})[1])
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: (inserted_results.append(kwargs), {"id": "result-1", **kwargs})[1])
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post(
        "/api/sessions/sess-1/ac-mains-dips/readings",
        json={"condition_key": "dip_40pct_10cycles", "indication": "1000.0", "significant_fault": False, "remarks": None},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["passed"] is True
    assert body["significant_fault"] is False

    assert inserted_readings[0]["test_type"] == "ac_mains_dips"
    assert inserted_readings[0]["sequence_no"] == 3  # position of dip_40pct_10cycles in the fixed list
    assert inserted_results[0]["passed"] is True


def test_submit_reading_significant_fault_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post(
        "/api/sessions/sess-1/ac-mains-dips/readings",
        json={"condition_key": "dip_40pct_10cycles", "indication": "1005.0", "significant_fault": True, "remarks": "display blanked"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["passed"] is False
    assert body["remarks"] == "display blanked"


def test_submit_reading_baseline_row_ignores_client_significant_fault(monkeypatch):
    # The "without disturbance" baseline row has no fault check on the form
    # itself — the server forces significant_fault False (and passed True)
    # regardless of what the client sends, since the condition's
    # has_fault_check is False.
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post(
        "/api/sessions/sess-1/ac-mains-dips/readings",
        json={"condition_key": "baseline", "indication": "1000.0", "significant_fault": True},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["significant_fault"] is False
    assert body["passed"] is True


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post(
        "/api/sessions/sess-1/ac-mains-dips/readings",
        json={"condition_key": "dip_0pct_1cycle", "indication": "1000", "significant_fault": False},
    )
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


def test_list_readings_dedupes_to_latest_per_condition(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-old", "sequence_no": 1, "data": {"condition_key": "dip_0pct_0.5cycle", "indication": "999", "significant_fault": True, "remarks": "flicker"}, "created_at": "t1"},
        {"id": "r-new", "sequence_no": 1, "data": {"condition_key": "dip_0pct_0.5cycle", "indication": "1000", "significant_fault": False, "remarks": None}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-old", "result": {}, "passed": False},
        {"reading_id": "r-new", "result": {}, "passed": True},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/ac-mains-dips/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["passed"] is True
    assert body[0]["indication"] == "1000"


def test_electrical_bursts_conditions_and_submit(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    conditions_resp = client.get("/api/sessions/sess-1/electrical-bursts/conditions")
    assert conditions_resp.status_code == 200
    assert len(conditions_resp.json()) == 18

    resp = client.post(
        "/api/sessions/sess-1/electrical-bursts/readings",
        json={"condition_key": "a_l_pos", "indication": "1000", "significant_fault": False},
    )
    assert resp.status_code == 201


def test_electrostatic_discharges_conditions_and_submit(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: {"id": "result-1", **kwargs})
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    conditions_resp = client.get("/api/sessions/sess-1/electrostatic-discharges/conditions")
    assert conditions_resp.status_code == 200
    assert len(conditions_resp.json()) == 26

    resp = client.post(
        "/api/sessions/sess-1/electrostatic-discharges/readings",
        json={"condition_key": "a_2kv_pos", "indication": "1000", "significant_fault": False},
    )
    assert resp.status_code == 201
