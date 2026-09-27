"""Pydantic v2 contract tests for the PUBLIC verification surface
(app.contracts.verify) — proves the safe-field-list model rejects
anything not on that list, so a future accidental addition of a
sensitive field to a row dict would fail loudly here, not leak silently.
"""

import pytest
from pydantic import ValidationError

from app.contracts.verify import DiscrepancyReportIn, PublicCertificateOut

_VALID_ROW = {
    "certificate_number": "SC-2026-000001",
    "status": "issued",
    "instrument_model": "X100",
    "instrument_manufacturer": "Acme Scales",
    "instrument_type_designation": "TD-1",
    "accuracy_class": "III",
    "verification_type": "initial",
    "issued_at": "2026-01-05T10:00:00Z",
}


def test_public_certificate_out_accepts_the_safe_field_list():
    out = PublicCertificateOut(**_VALID_ROW)
    assert out.certificate_number == "SC-2026-000001"
    assert out.status.value == "issued"


def test_public_certificate_out_rejects_any_extra_field():
    # extra="forbid" — proves the model can never silently pass through a
    # field nobody explicitly listed as safe. Simulates what would happen
    # if a future change to get_public_certificate_info() accidentally
    # started selecting a sensitive column (e.g. created_by).
    with pytest.raises(ValidationError):
        PublicCertificateOut(**_VALID_ROW, created_by="user-123")


@pytest.mark.parametrize(
    "sensitive_field",
    ["created_by", "approved_by", "session_id", "instrument_id", "remarks", "observer_name", "id"],
)
def test_public_certificate_out_rejects_every_known_sensitive_field(sensitive_field):
    with pytest.raises(ValidationError):
        PublicCertificateOut(**_VALID_ROW, **{sensitive_field: "should-never-appear"})


def test_public_certificate_out_requires_status_issued_shaped_but_does_not_itself_enforce_the_value():
    # The model validates SHAPE only — it's the DB function's WHERE clause
    # (status = 'issued') that guarantees a non-issued row never reaches
    # this model at all (ADR-0009). The model still accepts any valid
    # SessionStatus value, since that's a shape question, not a policy one.
    out = PublicCertificateOut(**{**_VALID_ROW, "status": "draft"})
    assert out.status.value == "draft"


def test_discrepancy_report_in_requires_non_empty_description():
    with pytest.raises(ValidationError):
        DiscrepancyReportIn(description="")


def test_discrepancy_report_in_contact_is_optional():
    payload = DiscrepancyReportIn(description="The QR code led to the wrong certificate.")
    assert payload.contact is None


def test_discrepancy_report_in_accepts_contact():
    payload = DiscrepancyReportIn(description="Load 4 looks wrong.", contact="citizen@example.com")
    assert payload.contact == "citizen@example.com"


def test_discrepancy_report_in_rejects_extra_fields():
    with pytest.raises(ValidationError):
        DiscrepancyReportIn(description="x", certificate_number="SC-2026-000001")
