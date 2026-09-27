"""Pydantic v2 contracts for the PUBLIC, login-free verification surface
(`GET /verify/{certificate_number}`, `POST /verify/{certificate_number}/report-discrepancy`).

Deliberately its own module, never sharing a model with
`app.contracts.session.SessionOut`: `PublicCertificateOut` is a narrow,
hand-picked safe field list, matching EXACTLY what
`db/schema.sql`'s `get_public_certificate_info()` SELECTs — see ADR-0009.
Never add a field here without adding it to that function's own SELECT
list first; the DB function is what decides what's safe to expose, this
model only validates the shape of what it already decided.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import SessionStatus
from engine.types import AccuracyClass, VerificationType


class PublicCertificateOut(BaseModel):
    """Exactly the columns `get_public_certificate_info()` returns.
    Deliberately excludes: technician/approver identity, raw readings,
    internal ids, remarks, or anything from a non-issued session (the
    function's own WHERE clause makes a non-issued session's row
    unreachable in the first place — this model never even sees one)."""

    model_config = ConfigDict(extra="forbid")

    certificate_number: str
    status: SessionStatus
    instrument_model: Optional[str] = None
    instrument_manufacturer: Optional[str] = None
    instrument_type_designation: Optional[str] = None
    accuracy_class: AccuracyClass
    verification_type: VerificationType
    issued_at: str


class DiscrepancyReportIn(BaseModel):
    """What anyone (no auth) submits via the public verify page's "Report
    a discrepancy" form. `contact` is optional — a reporter may prefer to
    stay anonymous."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=4000)
    contact: Optional[str] = Field(default=None, max_length=500)
