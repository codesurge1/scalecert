"""Router-level tests for runs/conditions on the Weighing endpoints
(feat/test-runs-conditions) — DB layer entirely mocked, same pattern as
test_voltage_variations_router.py. Covers: run creation, run listing,
run-scoped reading submission/listing, cross-run comparison, and — the
critical requirement — that every existing run-less (implicit default run)
Weighing flow keeps working unchanged when run_id is simply omitted.
"""

import app.repositories.instruments as instruments_repo
import app.repositories.readings as readings_repo
import app.repositories.runs as runs_repo
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

_VALID_READING_BODY = {"sequence_no": 0, "direction": "up", "I": "10.4", "delta_l": "0.5", "E0": "0"}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def _mock_session_and_instrument(monkeypatch, session_row=None):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: session_row or _DRAFT_SESSION_ROW)
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: _INSTRUMENT_ROW)


# ---------------------------------------------------------------------------
# Run creation / listing
# ---------------------------------------------------------------------------


def test_list_runs_returns_empty_list_when_none_created(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(runs_repo, "list_runs", lambda client, session_id, test_type: [])

    resp = client.get("/api/sessions/sess-1/weighing/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_run_404_when_session_not_found(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: None)
    resp = client.post("/api/sessions/does-not-exist/weighing/runs", json={"run_label": "at 40 C"})
    assert resp.status_code == 404


def test_create_run_409_when_session_not_draft(monkeypatch):
    _mock_session_and_instrument(monkeypatch, dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/weighing/runs", json={"run_label": "at 40 C"})
    assert resp.status_code == 409


def test_create_run_assigns_ordinal_one_past_existing_runs(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo,
        "list_runs",
        lambda client, session_id, test_type: [{"id": "run-0", "ordinal": 0}],
    )

    inserted = {}

    def fake_insert_run(client, **kwargs):
        inserted.update(kwargs)
        return {
            "id": "run-1",
            "session_id": kwargs["session_id"],
            "test_type": kwargs["test_type"],
            "run_label": kwargs["run_label"],
            "conditions": kwargs["conditions"],
            "ordinal": kwargs["ordinal"],
            "created_by": kwargs["created_by"],
            "created_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(runs_repo, "insert_run", fake_insert_run)

    resp = client.post(
        "/api/sessions/sess-1/weighing/runs",
        json={"run_label": "at 40 °C", "conditions": {"temperature_c": 40}},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["run_label"] == "at 40 °C"
    assert body["ordinal"] == 1
    assert body["test_type"] == "weighing"
    assert inserted["ordinal"] == 1
    assert inserted["conditions"] == {"temperature_c": 40}


# ---------------------------------------------------------------------------
# Backwards compatibility: submitting/listing readings without any run_id
# must behave exactly as before runs existed.
# ---------------------------------------------------------------------------


def test_submit_reading_without_run_id_stores_null_run_id(monkeypatch):
    _mock_session_and_instrument(monkeypatch)

    inserted_readings, inserted_results = [], []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: (inserted_readings.append(kwargs), {"id": "reading-1", **kwargs})[1])
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: (inserted_results.append(kwargs), {"id": "result-1", **kwargs})[1])
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/weighing/readings", json=_VALID_READING_BODY)
    assert resp.status_code == 201
    assert inserted_readings[0]["run_id"] is None
    assert inserted_results[0]["run_id"] is None


def test_submit_reading_with_unknown_run_id_is_rejected(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(runs_repo, "get_run", lambda client, run_id: None)

    resp = client.post("/api/sessions/sess-1/weighing/readings", json=dict(_VALID_READING_BODY, run_id="does-not-exist"))
    assert resp.status_code == 422


def test_submit_reading_with_run_id_from_another_session_is_rejected(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo,
        "get_run",
        lambda client, run_id: {"id": run_id, "session_id": "some-other-session", "test_type": "weighing"},
    )

    resp = client.post("/api/sessions/sess-1/weighing/readings", json=dict(_VALID_READING_BODY, run_id="run-x"))
    assert resp.status_code == 422


def test_submit_reading_with_valid_run_id_is_recorded_against_it(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo,
        "get_run",
        lambda client, run_id: {"id": run_id, "session_id": "sess-1", "test_type": "weighing"},
    )

    inserted_readings, inserted_results = [], []
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: (inserted_readings.append(kwargs), {"id": "reading-1", **kwargs})[1])
    monkeypatch.setattr(readings_repo, "insert_result", lambda client, **kwargs: (inserted_results.append(kwargs), {"id": "result-1", **kwargs})[1])
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/weighing/readings", json=dict(_VALID_READING_BODY, run_id="run-x"))
    assert resp.status_code == 201
    assert inserted_readings[0]["run_id"] == "run-x"
    assert inserted_results[0]["run_id"] == "run-x"


def test_list_readings_defaults_to_the_null_run_id(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-default", "sequence_no": 0, "direction": "up", "run_id": None, "data": {"I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t1"},
        {"id": "r-other-run", "sequence_no": 0, "direction": "up", "run_id": "run-x", "data": {"I": "20", "delta_l": "0", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-default", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-other-run", "result": {"E": "5", "Ec": "5", "mpe": "0.5"}, "passed": False},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/weighing/readings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["I"] == "10.4"
    assert body[0]["run_id"] is None


def test_list_readings_filters_by_explicit_run_id(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-default", "sequence_no": 0, "direction": "up", "run_id": None, "data": {"I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t1"},
        {"id": "r-other-run", "sequence_no": 0, "direction": "up", "run_id": "run-x", "data": {"I": "20", "delta_l": "0", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-default", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-other-run", "result": {"E": "5", "Ec": "5", "mpe": "0.5"}, "passed": False},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/weighing/readings", params={"run_id": "run-x"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["I"] == "20"
    assert body[0]["run_id"] == "run-x"


# ---------------------------------------------------------------------------
# Cross-run comparison
# ---------------------------------------------------------------------------


def test_compare_runs_returns_variation_error_per_matched_load(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-default", "sequence_no": 0, "direction": "up", "run_id": None, "data": {"I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t1"},
        {"id": "r-hot", "sequence_no": 0, "direction": "up", "run_id": "run-hot", "data": {"I": "10.9", "delta_l": "0.5", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-default", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-hot", "result": {"E": "0.6", "Ec": "0.6", "mpe": "0.5"}, "passed": False},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/weighing/runs/compare", params={"run_id_b": "run-hot"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    entry = body[0]
    assert entry["Ec_a"] == "0.1"
    assert entry["Ec_b"] == "0.6"
    assert entry["variation_error"] == "0.5"
    assert entry["passed"] is True  # variation_error == mpe, limit inclusive
    assert entry["run_id_a"] is None
    assert entry["run_id_b"] == "run-hot"


def test_compare_runs_empty_when_no_matching_loads(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: [])
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: [])

    resp = client.get("/api/sessions/sess-1/weighing/runs/compare", params={"run_id_b": "run-hot"})
    assert resp.status_code == 200
    assert resp.json() == []
