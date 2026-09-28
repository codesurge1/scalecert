"""Router-level tests for Endurance (clause 15) — DB layer entirely mocked,
same pattern as test_damp_heat_router.py, plus the two things unique to
this test: the b) cycling-step conditions PATCH and the durability
(all-loads-must-pass) endpoint.
"""

import app.repositories.instruments as instruments_repo
import app.repositories.readings as readings_repo
import app.repositories.runs as runs_repo
import app.repositories.sessions as sessions_repo
from app.deps import AuthContext, get_auth_context
from app.main import app
from app.repositories.errors import RepositoryError
from app.services.endurance import FINAL_RUN_LABEL, FIXED_RUN_LABELS
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


def test_setup_creates_both_fixed_runs_when_none_exist(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
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
        return row

    monkeypatch.setattr(runs_repo, "list_runs", fake_list_runs)
    monkeypatch.setattr(runs_repo, "insert_run", fake_insert_run)

    resp = client.post("/api/sessions/sess-1/endurance/setup")
    assert resp.status_code == 200
    body = resp.json()
    assert [run["run_label"] for run in body] == FIXED_RUN_LABELS
    assert [run["ordinal"] for run in body] == [0, 1]


def test_setup_409_when_session_not_draft(monkeypatch):
    _mock_session_and_instrument(monkeypatch, dict(_DRAFT_SESSION_ROW, status="submitted"))
    resp = client.post("/api/sessions/sess-1/endurance/setup")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# b) Performance of the test — cycling-step PATCH
# ---------------------------------------------------------------------------


def test_update_cycling_409_when_final_run_not_set_up_yet(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(runs_repo, "list_runs", lambda client, session_id, test_type: [])

    resp = client.patch(
        "/api/sessions/sess-1/endurance/cycling",
        json={"number_of_loadings": 100000, "load_applied": "1000"},
    )
    assert resp.status_code == 409


def test_update_cycling_happy_path_writes_to_the_final_run(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo,
        "list_runs",
        lambda client, session_id, test_type: [
            {"id": "run-initial", "run_label": FIXED_RUN_LABELS[0], "session_id": "sess-1", "test_type": "endurance",
             "conditions": None, "ordinal": 0, "created_by": _FAKE_AUTH.user_id, "created_at": "t"},
            {"id": "run-final", "run_label": FINAL_RUN_LABEL, "session_id": "sess-1", "test_type": "endurance",
             "conditions": None, "ordinal": 1, "created_by": _FAKE_AUTH.user_id, "created_at": "t"},
        ],
    )

    updated = {}

    def fake_update(client, *, run_id, conditions):
        updated["run_id"] = run_id
        updated["conditions"] = conditions
        return {
            "id": run_id, "session_id": "sess-1", "test_type": "endurance", "run_label": FINAL_RUN_LABEL,
            "conditions": conditions, "ordinal": 1, "created_by": _FAKE_AUTH.user_id, "created_at": "t",
        }

    monkeypatch.setattr(runs_repo, "update_run_conditions", fake_update)

    resp = client.patch(
        "/api/sessions/sess-1/endurance/cycling",
        json={"number_of_loadings": 100000, "load_applied": "1000"},
    )
    assert resp.status_code == 200
    assert resp.json()["conditions"] == {"number_of_loadings": 100000, "load_applied": "1000"}
    assert updated["run_id"] == "run-final"  # derived server-side, never client-supplied


def test_update_cycling_fields_are_optional(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo,
        "list_runs",
        lambda client, session_id, test_type: [
            {"id": "run-final", "run_label": FINAL_RUN_LABEL, "session_id": "sess-1", "test_type": "endurance",
             "conditions": None, "ordinal": 1, "created_by": _FAKE_AUTH.user_id, "created_at": "t"},
        ],
    )

    updated = {}
    monkeypatch.setattr(
        runs_repo,
        "update_run_conditions",
        lambda client, *, run_id, conditions: (updated.update(conditions=conditions), {
            "id": run_id, "session_id": "sess-1", "test_type": "endurance", "run_label": FINAL_RUN_LABEL,
            "conditions": conditions, "ordinal": 1, "created_by": _FAKE_AUTH.user_id, "created_at": "t",
        })[1],
    )

    resp = client.patch("/api/sessions/sess-1/endurance/cycling", json={"number_of_loadings": 5000})
    assert resp.status_code == 200
    assert updated["conditions"] == {"number_of_loadings": 5000}


# ---------------------------------------------------------------------------
# Reading submission, run-scoped
# ---------------------------------------------------------------------------


def test_submit_reading_rejects_unknown_run(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(runs_repo, "get_run", lambda client, run_id: None)
    resp = client.post("/api/sessions/sess-1/endurance/readings", json=dict(_VALID_READING_BODY, run_id="nope"))
    assert resp.status_code == 422


def test_submit_reading_happy_path(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo, "get_run", lambda client, run_id: {"id": run_id, "session_id": "sess-1", "test_type": "endurance"}
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

    resp = client.post("/api/sessions/sess-1/endurance/readings", json=dict(_VALID_READING_BODY, run_id="run-initial"))
    assert resp.status_code == 201
    assert inserted_readings[0]["test_type"] == "endurance"
    assert inserted_readings[0]["run_id"] == "run-initial"


def test_submit_reading_rolls_back_reading_when_result_insert_fails(monkeypatch):
    _mock_session_and_instrument(monkeypatch)
    monkeypatch.setattr(
        runs_repo, "get_run", lambda client, run_id: {"id": run_id, "session_id": "sess-1", "test_type": "endurance"}
    )
    monkeypatch.setattr(readings_repo, "insert_reading", lambda client, **kwargs: {"id": "reading-1", **kwargs})

    def failing_insert_result(client, **kwargs):
        raise RepositoryError(table="test_results", operation="insert", hint="boom", likely_rls=False)

    deleted_ids = []
    monkeypatch.setattr(readings_repo, "insert_result", failing_insert_result)
    monkeypatch.setattr(readings_repo, "delete_reading", lambda client, reading_id: deleted_ids.append(reading_id))

    resp = client.post("/api/sessions/sess-1/endurance/readings", json=dict(_VALID_READING_BODY, run_id="run-initial"))
    assert resp.status_code == 500
    assert deleted_ids == ["reading-1"]


# ---------------------------------------------------------------------------
# Durability check (the all-loads-must-pass aggregate)
# ---------------------------------------------------------------------------


def test_durability_409_when_runs_not_set_up_yet(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(runs_repo, "list_runs", lambda client, session_id, test_type: [])

    resp = client.get("/api/sessions/sess-1/endurance/durability")
    assert resp.status_code == 409


def test_durability_all_passed_when_every_load_within_mpe(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(
        runs_repo,
        "list_runs",
        lambda client, session_id, test_type: [
            {"id": "run-initial", "run_label": FIXED_RUN_LABELS[0], "session_id": "sess-1", "test_type": "endurance",
             "conditions": None, "ordinal": 0, "created_by": _FAKE_AUTH.user_id, "created_at": "t"},
            {"id": "run-final", "run_label": FIXED_RUN_LABELS[1], "session_id": "sess-1", "test_type": "endurance",
             "conditions": None, "ordinal": 1, "created_by": _FAKE_AUTH.user_id, "created_at": "t"},
        ],
    )

    reading_rows = [
        {"id": "r-i", "sequence_no": 0, "direction": "up", "run_id": "run-initial", "data": {"I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t1"},
        {"id": "r-f", "sequence_no": 0, "direction": "up", "run_id": "run-final", "data": {"I": "10.5", "delta_l": "0.5", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-i", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-f", "result": {"E": "0.2", "Ec": "0.2", "mpe": "0.5"}, "passed": True},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/endurance/durability")
    assert resp.status_code == 200
    body = resp.json()
    assert body["all_passed"] is True
    assert len(body["comparisons"]) == 1
    assert body["comparisons"][0]["variation_error"] == "0.1"


def test_durability_fails_when_one_load_exceeds_mpe(monkeypatch):
    monkeypatch.setattr(sessions_repo, "get_session", lambda client, session_id: _DRAFT_SESSION_ROW)
    monkeypatch.setattr(
        runs_repo,
        "list_runs",
        lambda client, session_id, test_type: [
            {"id": "run-initial", "run_label": FIXED_RUN_LABELS[0], "session_id": "sess-1", "test_type": "endurance",
             "conditions": None, "ordinal": 0, "created_by": _FAKE_AUTH.user_id, "created_at": "t"},
            {"id": "run-final", "run_label": FIXED_RUN_LABELS[1], "session_id": "sess-1", "test_type": "endurance",
             "conditions": None, "ordinal": 1, "created_by": _FAKE_AUTH.user_id, "created_at": "t"},
        ],
    )

    reading_rows = [
        {"id": "r-i", "sequence_no": 0, "direction": "up", "run_id": "run-initial", "data": {"I": "10.4", "delta_l": "0.5", "E0": "0"}, "created_at": "t1"},
        {"id": "r-f", "sequence_no": 0, "direction": "up", "run_id": "run-final", "data": {"I": "11.1", "delta_l": "0.5", "E0": "0"}, "created_at": "t2"},
    ]
    result_rows = [
        {"reading_id": "r-i", "result": {"E": "0.1", "Ec": "0.1", "mpe": "0.5"}, "passed": True},
        {"reading_id": "r-f", "result": {"E": "0.8", "Ec": "0.8", "mpe": "0.5"}, "passed": False},
    ]
    monkeypatch.setattr(readings_repo, "list_readings", lambda client, session_id, test_type: reading_rows)
    monkeypatch.setattr(readings_repo, "list_results", lambda client, session_id, test_type: result_rows)

    resp = client.get("/api/sessions/sess-1/endurance/durability")
    assert resp.status_code == 200
    body = resp.json()
    assert body["all_passed"] is False  # variation_error = |0.1 - 0.8| = 0.7 > mpe 0.5
