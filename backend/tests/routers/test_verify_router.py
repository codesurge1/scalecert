"""Router-level tests for the PUBLIC, login-free verification surface
(app/routers/verify.py). The DB layer is entirely mocked (monkeypatched
`app.repositories.public` functions) — no live Supabase, and deliberately
NO auth override at all: these routes must work with zero setup, proving
they really are reachable without any authentication.
"""

import app.repositories.public as public_repo
from app.main import app
from app.repositories.errors import RepositoryError
from fastapi.testclient import TestClient

client = TestClient(app)

_ISSUED_ROW = {
    "certificate_number": "SC-2026-000001",
    "status": "issued",
    "instrument_model": "X100",
    "instrument_manufacturer": "Acme Scales",
    "instrument_type_designation": "TD-1",
    "accuracy_class": "III",
    "verification_type": "initial",
    "issued_at": "2026-01-05T10:00:00Z",
}


def test_verify_issued_certificate_returns_safe_fields(monkeypatch):
    monkeypatch.setattr(public_repo, "get_public_certificate_info", lambda client, cert_number: dict(_ISSUED_ROW))

    resp = client.get("/api/verify/SC-2026-000001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["certificate_number"] == "SC-2026-000001"
    assert body["status"] == "issued"
    assert body["instrument_model"] == "X100"


def test_verify_response_never_contains_a_sensitive_field(monkeypatch):
    # Even if the repository layer somehow returned extra keys (it never
    # should — get_public_certificate_info()'s own SELECT list is fixed,
    # ADR-0009), PublicCertificateOut's extra="forbid" would reject them
    # rather than pass them through. Here we confirm the actual response
    # body — the thing a real client sees — carries ONLY the safe fields.
    monkeypatch.setattr(public_repo, "get_public_certificate_info", lambda client, cert_number: dict(_ISSUED_ROW))
    resp = client.get("/api/verify/SC-2026-000001")
    assert resp.status_code == 200
    body = resp.json()
    sensitive_fields = {
        "created_by", "approved_by", "session_id", "instrument_id", "id",
        "remarks", "observer_name", "technician", "approver", "readings",
    }
    assert sensitive_fields.isdisjoint(body.keys())
    assert set(body.keys()) == {
        "certificate_number", "status", "instrument_model", "instrument_manufacturer",
        "instrument_type_designation", "accuracy_class", "verification_type", "issued_at",
    }


def test_verify_returns_404_when_certificate_does_not_exist(monkeypatch):
    monkeypatch.setattr(public_repo, "get_public_certificate_info", lambda client, cert_number: None)
    resp = client.get("/api/verify/SC-2026-999999")
    assert resp.status_code == 404


def test_verify_returns_404_for_a_draft_session_never_leaking_that_it_exists(monkeypatch):
    # get_public_certificate_info() itself returns None for this case
    # (its own WHERE clause excludes non-issued statuses) — the repo
    # function's contract is "None means not found OR not issued,
    # indistinguishably" (ADR-0009), so mocking None here IS the correct
    # simulation of "a draft session exists with this certificate_number."
    monkeypatch.setattr(public_repo, "get_public_certificate_info", lambda client, cert_number: None)
    resp = client.get("/api/verify/SC-2026-000002")
    assert resp.status_code == 404
    # The 404 body must be identical in shape to the nonexistent-certificate
    # case — no extra hint distinguishing "exists but not issued".
    assert resp.json() == {"detail": "certificate not found"}


def test_verify_maps_repository_error_to_500(monkeypatch):
    def failing(client, cert_number):
        raise RepositoryError(table="test_sessions", operation="rpc", hint="db unreachable", likely_rls=False)

    monkeypatch.setattr(public_repo, "get_public_certificate_info", failing)
    resp = client.get("/api/verify/SC-2026-000001")
    assert resp.status_code == 500


def test_verify_requires_no_authorization_header_at_all(monkeypatch):
    # No Authorization header is sent at all — this is the whole point of
    # the endpoint. Confirms it isn't accidentally gated by
    # Depends(get_auth_context) the way every other route in this app is.
    monkeypatch.setattr(public_repo, "get_public_certificate_info", lambda client, cert_number: dict(_ISSUED_ROW))
    resp = client.get("/api/verify/SC-2026-000001", headers={})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# report-discrepancy
# ---------------------------------------------------------------------------
def test_report_discrepancy_happy_path(monkeypatch):
    captured = []
    monkeypatch.setattr(
        public_repo,
        "insert_discrepancy_report",
        lambda client, **kwargs: captured.append(kwargs) or {"id": "report-1", **kwargs},
    )
    resp = client.post(
        "/api/verify/SC-2026-000001/report-discrepancy",
        json={"description": "The QR code points to the wrong page.", "contact": "citizen@example.com"},
    )
    assert resp.status_code == 201
    assert captured[0]["certificate_number"] == "SC-2026-000001"
    assert captured[0]["description"] == "The QR code points to the wrong page."
    assert captured[0]["contact"] == "citizen@example.com"


def test_report_discrepancy_contact_is_optional(monkeypatch):
    captured = []
    monkeypatch.setattr(
        public_repo,
        "insert_discrepancy_report",
        lambda client, **kwargs: captured.append(kwargs) or {"id": "report-1", **kwargs},
    )
    resp = client.post("/api/verify/SC-2026-000001/report-discrepancy", json={"description": "Something looks off."})
    assert resp.status_code == 201
    assert captured[0]["contact"] is None


def test_report_discrepancy_rejects_empty_description():
    resp = client.post("/api/verify/SC-2026-000001/report-discrepancy", json={"description": ""})
    assert resp.status_code == 422


def test_report_discrepancy_does_not_require_the_certificate_to_exist(monkeypatch):
    # Deliberate (see app/routers/verify.py): validating existence here
    # would itself leak the exact distinction GET /verify is careful never
    # to leak (real-but-not-issued vs. never existed).
    captured = []
    monkeypatch.setattr(
        public_repo,
        "insert_discrepancy_report",
        lambda client, **kwargs: captured.append(kwargs) or {"id": "report-1", **kwargs},
    )
    resp = client.post(
        "/api/verify/SC-NOT-A-REAL-NUMBER/report-discrepancy", json={"description": "Testing a bogus number."}
    )
    assert resp.status_code == 201
    assert captured[0]["certificate_number"] == "SC-NOT-A-REAL-NUMBER"


def test_report_discrepancy_maps_likely_rls_repository_error_to_403(monkeypatch):
    def failing(client, **kwargs):
        raise RepositoryError(table="discrepancy_reports", operation="insert", hint="RLS rejected it", likely_rls=True)

    monkeypatch.setattr(public_repo, "insert_discrepancy_report", failing)
    resp = client.post("/api/verify/SC-2026-000001/report-discrepancy", json={"description": "x"})
    assert resp.status_code == 403


def test_report_discrepancy_requires_no_authorization_header_at_all(monkeypatch):
    monkeypatch.setattr(public_repo, "insert_discrepancy_report", lambda client, **kwargs: {"id": "report-1", **kwargs})
    resp = client.post(
        "/api/verify/SC-2026-000001/report-discrepancy", json={"description": "x"}, headers={}
    )
    assert resp.status_code == 201
