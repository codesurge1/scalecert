"""Router-level tests for Damp heat (clause 13) — DB layer entirely mocked,
same pattern as test_weighing_runs_router.py: the fixed a/b/c run setup,
run-scoped reading submission/listing, and the cross-run comparison.
"""

import app.repositories.instruments as instruments_repo
import app.repositories.readings as readings_repo
import app.repositories.runs as runs_repo
import app.repositories.sessions as sessions_repo
from app.deps import AuthContext, get_auth_context
from app.main import app
from app.repositories.errors import RepositoryError
from app.services.damp_heat import FIXED_RUN_LABELS
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
# Fixed run setup
# ---------------------------------------------------------------------------


def test_setup_creates_all_three_fixed_runs_when_none_exist(monkeypatch):
    _mock_session_and_instrument(monkeypatch)

    created = []
    state = {"runs": []}

    def fake_list_runs(client, session_id, test_type):
        return list(state["runs"])

    def fake_insert_run(client, **kwargs):
        row = {
            "id": f"run-{len(state['runs'])}",
            "session_id": kwargs["session_id"],
            "test_type": kwargs["test_type"],
            "run_label": kwargs["run_label"],
            "conditions": kwargs["conditions"],
            "ordinal": kwargs["ordinal"],
            "created_by": kwargs["created_by"],
            "created_at": "2026-01-01T00:00:00Z",
        }
        state["runs"].append(row)
        created.append(kwargs["run_label"])
        return row

    monkeypatch.setattr(runs_repo, "list_runs", fake_list_runs)
    monkeypatch.setattr(runs_repo, "insert_run", fake_insert_run)

    resp = client.post("/api/sessions/sess-1/damp-heat/setup")
    assert resp.status_code == 200
    body = resp.json()
    assert [run["run_label"] for run in body] == FIXED_RUN_LABELS
    assert [run["ordinal"] for run in body] == [0, 1, 2]
    assert created == FIXED_RUN_LABELS


def test_setup_is_idempotent_when_runs_already_exist(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    existing = [
        {"id": f"run-{i}", "session_id": "sess-1", "test_type": "damp_heat", "run_label": label,
         "conditions": None, "ordinal": i, "created_by": _FAKE_AUTH.user_id, "created_at": "t"}
        for i, label in enumerate(FIXED_RUN_LABELS)
    ]
    monkeypatch.setattr(runs_repo, "list_runs", lambda client, session_id, test_type: existing)

    def fail_insert(client, **kwargs):
        raise AssertionError("should not insert when all fixed runs already exist")

    monkeypatch.setattr(runs_repo, "insert_run", fail_insert)

    resp = client.post("/api/sessions/sess-1/damp-heat/setup")
    assert resp.status_code == 200
    assert [run["run_label"] for run in resp.json()] == FIXED_RUN_LABELS


def test_setup_409_when_session_not_draft(monkeypatch):
    _mock_session_and_instrument(monkeypatch, dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/damp-heat/setup")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Reading submission / listing, run-scoped
# ---------------------------------------------------------------------------


def test_submit_reading_requires_a_valid_run_belonging_to_this_session(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(runs_repo, "get_run", lambda client, run_id: None)

    resp = client.post("/api/sessions/sess-1/damp-heat/readings", json=dict(_VALID_READING_BODY, run_id="does-not-exist"))
    assert resp.status_code == 422


def test_submit_reading_rejects_run_from_a_different_test_type(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo, "get_run", lambda client, run_id: {"id": run_id, "session_id": "sess-1", "test_type": "weighing"}
    )
    resp = client.post("/api/sessions/sess-1/damp-heat/readings", json=dict(_VALID_READING_BODY, run_id="run-x"))
    assert resp.status_code == 422


def test_submit_reading_happy_path_writes_reading_and_result_tagged_with_run(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo, "get_run", lambda client, run_id: {"id": run_id, "session_id": "sess-1", "test_type": "damp_heat"}
    )

    inserted_readings, inserted_results = [], []
    monkeypatch.setattr(
        readings_repo, "insert_reading",
        lambda client, **kwargs: (inserted_readings.append(kwargs), {"id": "reading-1", **kwargs})[1],
    )
    monkeypatch.setattr(
        readings_repo, "insert_result",
        lambda client, **kwargs: (inserted_results.append(kwargs), {"id": "result-1", **kwargs})[1],
    )
    monkeypatch.setattr(readings_repo, "insert_audit_log", lambda client, **kwargs: None)

    resp = client.post("/api/sessions/sess-1/damp-heat/readings", json=dict(_VALID_READING_BODY, run_id="run-a"))
    assert resp.status_code == 201
    assert inserted_readings[0]["test_type"] == "damp_heat"
    assert inserted_readings[0]["run_id"] == "run-a"
    assert inserted_results[0]["test_type"] == "damp_heat"
    assert inserted_results[0]["run_id"] == "run-a"


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo, "get_run", lambda client, run_id: {"id": run_id, "session_id": "sess-1", "test_type": "damp_heat"}
    )
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/damp-heat/readings", json=dict(_VALID_READING_BODY, run_id="run-a"))
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


def test_list_readings_filters_by_run_id(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-a", "sequence_no": 0, "direction": "up", "run_id": "run-a", "data": {"I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t1"},
        {"id": "r-c", "sequence_no": 0, "direction": "up", "run_id": "run-c", "data": {"I": "20", "delta_l": "0", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-a", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-c", "result": {"E": "5", "Ec": "5", "mpe": "0.5"}, "passed": False},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/damp-heat/readings", params={"run_id": "run-c"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["I"] == "20"
    assert body[0]["run_id"] == "run-c"


def test_compare_runs_surfaces_drift_between_runs(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)

    reading_rows = [
        {"id": "r-a", "sequence_no": 0, "direction": "up", "run_id": "run-a", "data": {"I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t1"},
        {"id": "r-c", "sequence_no": 0, "direction": "up", "run_id": "run-c", "data": {"I": "10.9", "delta_l": "0.5", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-a", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-c", "result": {"E": "0.6", "Ec": "0.6", "mpe": "0.5"}, "passed": False},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/damp-heat/runs/compare", params={"run_id_a": "run-a", "run_id_b": "run-c"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["variation_error"] == "0.5"
    assert body[0]["passed"] is True  # variation_error == mpe, limit inclusive
