"""The PUBLIC, login-free verification surface — no `Depends(get_auth_context)`
anywhere in this module, deliberately: this is the one part of the API a
citizen or inspector with no ScaleCert account is meant to reach. See
ADR-0009 for why calling one `SECURITY DEFINER` function through the anon
client is safe: that function itself enforces `status = 'issued'` and a
fixed safe field list, so this grants no broader access than what any
visitor is already meant to see.
"""

from fastapi import APIRouter, HTTPException

from app.contracts.verify import DiscrepancyReportIn, PublicCertificateOut
from app.repositories import public as public_repo
from app.repositories.errors import RepositoryError
from app.supabase_client import anon_client

router = APIRouter(prefix="/verify", tags=["verify"])


@router.get("/{certificate_number}", response_model=PublicCertificateOut)
def get_public_certificate(certificate_number: str) -> PublicCertificateOut:
    client = anon_client()
    try:
        row = public_repo.get_public_certificate_info(client, certificate_number)
    except RepositoryError as exc:
        raise HTTPException(
            status_code=500, detail=f"could not look up this certificate ({exc.hint})"
        ) from exc

    if row is None:
        # Deliberately the SAME 404 whether the certificate number never
        # existed or belongs to a session that isn't `issued`
        # (draft/submitted/approved/returned/superseded) — never leaking
        # which, per this task's own requirement.
        raise HTTPException(status_code=404, detail="certificate not found")
    return PublicCertificateOut(**row)


@router.post("/{certificate_number}/report-discrepancy", status_code=201)
def report_discrepancy(certificate_number: str, payload: DiscrepancyReportIn) -> dict:
    """No existence/issued check against `certificate_number` before
    accepting a report — a deliberate simplification (see SESSION_LOG.md),
    not a gap this task treats as blocking: rejecting an unrecognized
    number here would itself leak information the public GET route above
    is careful never to leak (whether a given number belongs to a
    non-issued session vs. not existing at all)."""
    client = anon_client()
    try:
        public_repo.insert_discrepancy_report(
            client,
            certificate_number=certificate_number,
            description=payload.description,
            contact=payload.contact,
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not record this report ({exc.hint})",
        ) from exc
    return {"status": "received"}
