"""Router-level tests for /api/instruments — DB layer entirely mocked."""

import app.repositories.instruments as instruments_repo
from app.deps import AuthContext, get_auth_context
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

_FAKE_AUTH = AuthContext(client=object(), user_id="11111111-1111-1111-1111-111111111111", token="tok")

_VALID_BODY = {
    "accuracy_class": "III",
    "e_value": "1",
    "max_capacity": "5000",
    "min_capacity": "10",
    "indication_type": "digital",
}


def setup_module(_module):
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH


def teardown_module(_module):
    app.dependency_overrides.clear()


def test_create_instrument_sets_registered_by_and_returns_row(monkeypatch):
    captured = {}

    def fake_insert(client, registered_by, payload):
        captured["registered_by"] = registered_by
        return {
            "id": "instr-1",
            "registered_by": registered_by,
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

    monkeypatch.setattr(instruments_repo, "insert_instrument", fake_insert)

    resp = client.post("/api/instruments", json=_VALID_BODY)
    assert resp.status_code == 201
    assert captured["registered_by"] == _FAKE_AUTH.user_id
    body = resp.json()
    assert body["e_value"] == "1.0"  # string, not a JSON number (exact — from Decimal(str(1.0)))
    assert body["registered_by"] == _FAKE_AUTH.user_id


def test_create_instrument_rejects_invalid_body():
    resp = client.post("/api/instruments", json={"accuracy_class": "V"})
    assert resp.status_code == 422


def test_get_instrument_404_when_not_found(monkeypatch):
    monkeypatch.setattr(instruments_repo, "get_instrument", lambda client, instrument_id: None)
    resp = client.get("/api/instruments/does-not-exist")
    assert resp.status_code == 404


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
