"""Router-level tests for /api/instruments — DB layer entirely mocked."""

from decimal import Decimal as D

import app.repositories.instruments as instruments_repo
import app.repositories.sessions as sessions_repo
from app.deps import AuthContext, get_auth_context
from app.main import app
from app.repositories.errors import RepositoryError
from fastapi.testclient import TestClient

client = TestClient(app)

_FAKE_AUTH = AuthContext(client=object(), user_id="11111111-1111-1111-1111-111111111111", token="tok")

# e=1g, Max=6000g -> n=6000, uniquely Class III (fits III's [100,10000] with
# Min=20>=20e=20g; also within Class II's high-e-row n-range [5000,100000],
# but fails that row's Min>=50e=50g requirement, so only III qualifies) — no
# accuracy_class in the body at all, proving derivation works without one.
_VALID_BODY = {
    "e_value": "1",
    "max_capacity": "6000",
    "min_capacity": "20",
    "indication_type": "digital",
}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_create_instrument_sets_registered_by_and_returns_row(monkeypatch):
    captured = {}

    def fake_insert(client, registered_by, payload, accuracy_class):
        captured["registered_by"] = registered_by
        captured["accuracy_class"] = accuracy_class
        return {
            "id": "instr-1",
            "registered_by": registered_by,
            "application_no": None,
            "type_designation": None,
            "manufacturer": None,
            "model": None,
            "serial_number": None,
            "accuracy_class": accuracy_class.value,
            "e_value": 1.0,
            "d_value": None,
            "max_capacity": 6000.0,
            "min_capacity": 20.0,
            "indication_type": "digital",
            "is_mobile": False,
            "is_multi_interval": False,
            "created_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(instruments_repo, "insert_instrument", fake_insert)

    resp = client.post("/api/instruments", json=_VALID_BODY)
    assert resp.status_code == 201
    assert captured["registered_by"] == _FAKE_AUTH.user_id
    assert captured["accuracy_class"].value == "III"  # derived, not client-submitted (body has no accuracy_class at all)
    body = resp.json()
    assert body["accuracy_class"] == "III"
    assert body["e_value"] == "1.0"  # string, not a JSON number (exact — from Decimal(str(1.0)))
    assert body["registered_by"] == _FAKE_AUTH.user_id


def test_create_instrument_rejects_invalid_body():
    resp = client.post("/api/instruments", json={"accuracy_class": "V"})
    assert resp.status_code == 422


def test_create_instrument_persists_page_6_fields(monkeypatch):
    captured = {}

    def fake_insert(client, registered_by, payload, accuracy_class):
        captured["payload"] = payload
        return {
            "id": "instr-1",
            "registered_by": registered_by,
            "application_no": None,
            "type_designation": None,
            "manufacturer": None,
            "model": None,
            "serial_number": None,
            "accuracy_class": accuracy_class.value,
            "e_value": 1.0,
            "d_value": None,
            "max_capacity": 6000.0,
            "min_capacity": 20.0,
            "indication_type": "digital",
            "is_mobile": False,
            "is_multi_interval": False,
            "applicant": "RRSL Mumbai",
            "u_nom": 230.0,
            "printer_status": "built_in",
            "created_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(instruments_repo, "insert_instrument", fake_insert)

    resp = client.post(
        "/api/instruments",
        json=dict(_VALID_BODY, applicant="RRSL Mumbai", u_nom="230", printer_status="built_in"),
    )
    assert resp.status_code == 201
    assert captured["payload"].applicant == "RRSL Mumbai"
    assert captured["payload"].u_nom == D("230")
    body = resp.json()
    assert body["applicant"] == "RRSL Mumbai"
    assert body["u_nom"] == "230.0"  # string, not a JSON number
    assert body["printer_status"] == "built_in"


def test_create_instrument_rejects_e_max_min_that_fit_no_class(monkeypatch):
    # n=20 with e=1g, Min=1g fits no Table 3 class at all — 422 with the
    # engine's own reason, and the DB is never touched.
    called = []
    monkeypatch.setattr(instruments_repo, "insert_instrument", lambda *a, **k: called.append(1))

    resp = client.post(
        "/api/instruments",
        json={"e_value": "1", "max_capacity": "20", "min_capacity": "1", "indication_type": "digital"},
    )
    assert resp.status_code == 422
    assert "No accuracy class fits" in resp.json()["detail"]
    assert called == []


def test_create_instrument_requires_disambiguation_when_multiple_classes_qualify(monkeypatch):
    # e=1g, Max=8000g (n=8000), Min=50g qualifies for both Class II and
    # Class III (see tests/test_classification.py's equivalent engine
    # case) — omitting accuracy_class must 422, not guess.
    called = []
    monkeypatch.setattr(instruments_repo, "insert_instrument", lambda *a, **k: called.append(1))

    resp = client.post(
        "/api/instruments",
        json={"e_value": "1", "max_capacity": "8000", "min_capacity": "50", "indication_type": "digital"},
    )
    assert resp.status_code == 422
    assert "more than one accuracy class" in resp.json()["detail"]
    assert called == []


def test_create_instrument_accepts_valid_disambiguation_among_multiple(monkeypatch):
    captured = {}

    def fake_insert(client, registered_by, payload, accuracy_class):
        captured["accuracy_class"] = accuracy_class
        return {
            "id": "instr-1",
            "registered_by": registered_by,
            "application_no": None,
            "type_designation": None,
            "manufacturer": None,
            "model": None,
            "serial_number": None,
            "accuracy_class": accuracy_class.value,
            "e_value": 1.0,
            "d_value": None,
            "max_capacity": 8000.0,
            "min_capacity": 50.0,
            "indication_type": "digital",
            "is_mobile": False,
            "is_multi_interval": False,
            "created_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(instruments_repo, "insert_instrument", fake_insert)

    resp = client.post(
        "/api/instruments",
        json={
            "e_value": "1",
            "max_capacity": "8000",
            "min_capacity": "50",
            "indication_type": "digital",
            "accuracy_class": "II",
        },
    )
    assert resp.status_code == 201
    assert captured["accuracy_class"].value == "II"


def test_create_instrument_rejects_disambiguation_not_among_the_qualifying_classes(monkeypatch):
    # Same multi-qualifying e/Max/Min as above (II or III), but the client
    # submits IIII — not one of the classes that actually qualify — 422.
    called = []
    monkeypatch.setattr(instruments_repo, "insert_instrument", lambda *a, **k: called.append(1))

    resp = client.post(
        "/api/instruments",
        json={
            "e_value": "1",
            "max_capacity": "8000",
            "min_capacity": "50",
            "indication_type": "digital",
            "accuracy_class": "IIII",
        },
    )
    assert resp.status_code == 422
    assert called == []


def test_create_instrument_maps_repository_error_to_403_when_likely_rls(monkeypatch):
    def failing_insert(client, registered_by, payload, accuracy_class):
        raise RepositoryError(table="instruments", operation="insert", hint="RLS rejected it", likely_rls=True)

    monkeypatch.setattr(instruments_repo, "insert_instrument", failing_insert)
    resp = client.post("/api/instruments", json=_VALID_BODY)
    assert resp.status_code == 403
    assert "instruments" in resp.json()["detail"]


def test_get_instrument_404_when_not_found(monkeypatch):
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: None)
    resp = client.get("/api/instruments/does-not-exist")
    assert resp.status_code == 404


def test_get_instrument_404_not_500_when_id_is_malformed(monkeypatch):
    # Before this task's fix, an APIError from a malformed id (e.g. Postgres's
    # "invalid input syntax for type uuid") was never caught anywhere in this
    # call chain and fell through as an unhandled, detail-free 500. It now
    # folds into the same clean 404 a genuinely missing instrument gets.
    def raise_malformed_id(client, instrument_id):
        raise RepositoryError(
            table="instruments",
            operation="select",
            hint="PostgREST error 22P02: invalid input syntax for type uuid",
            likely_rls=False,
        )

    monkeypatch.setattr(instruments_repo, "get_instrument", raise_malformed_id)
    resp = client.get("/api/instruments/not-a-uuid")
    assert resp.status_code == 404
    assert "22P02" in resp.json()["detail"]


def test_list_instruments_returns_rows(monkeypatch):
    monkeypatch.setattr(
        instruments_repo,
        "list_instruments",
        lambda client: [
            {
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
        ],
    )
    resp = client.get("/api/instruments")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_instrument_sessions_returns_rows(monkeypatch):
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: {"id": "instr-1"})
    monkeypatch.setattr(
        sessions_repo,
        "list_sessions_for_instrument",
        lambda client, instrument_id: [
            {
                "id": "sess-2",
                "instrument_id": "instr-1",
                "verification_type": "subsequent",
                "status": "draft",
                "created_by": _FAKE_AUTH.user_id,
                "created_at": "2026-01-02T00:00:00Z",
            },
            {
                "id": "sess-1",
                "instrument_id": "instr-1",
                "verification_type": "initial",
                "status": "issued",
                "created_by": _FAKE_AUTH.user_id,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ],
    )
    monkeypatch.setattr(sessions_repo, "get_session_test_selections", lambda client, session_id: [])

    resp = client.get("/api/instruments/instr-1/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert [row["id"] for row in body] == ["sess-2", "sess-1"]
    assert body[0]["verification_type"] == "subsequent"


def test_list_instrument_sessions_404_when_instrument_not_found(monkeypatch):
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: None)
    resp = client.get("/api/instruments/does-not-exist/sessions")
    assert resp.status_code == 404
