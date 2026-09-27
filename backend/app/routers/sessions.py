import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.contracts.common import IndicationType, SessionStatus, TestType
from app.contracts.discrimination import (
    DiscriminationCheckOut,
    DiscriminationReadingRecordOut,
    DiscriminationReadingSubmitIn,
    DiscriminationResultOut,
    reading_and_result_to_record_out as discrimination_reading_and_result_to_record_out,
)
from app.contracts.eccentricity import (
    EccentricityReadingRecordOut,
    EccentricityReadingSubmitIn,
    EccentricityResultOut,
    EccentricitySetupOut,
    reading_and_result_to_record_out as eccentricity_reading_and_result_to_record_out,
)
from app.contracts.instrument import instrument_out_from_row, instrument_params_from_row
from app.contracts.repeatability import RepeatabilityReadingSubmitIn, RepeatabilitySeriesOut
from app.contracts.sensitivity import (
    SensitivityCheckOut,
    SensitivityReadingRecordOut,
    SensitivityReadingSubmitIn,
    SensitivityResultOut,
    reading_and_result_to_record_out as sensitivity_reading_and_result_to_record_out,
)
from app.contracts.session import SessionIn, SessionOut, SessionReturnIn, session_out_from_rows
from app.contracts.tilting import TiltingReadingSubmitIn, TiltingStateOut
from app.contracts.weighing import (
    WeighingReadingRecordOut,
    WeighingReadingSubmitIn,
    WeighingResultOut,
    WeighingSequenceEntryOut,
    reading_and_result_to_record_out,
)
from app.contracts.zero_tare import (
    ZeroTareCheckOut,
    ZeroTareReadingRecordOut,
    ZeroTareReadingSubmitIn,
    ZeroTareResultOut,
    reading_and_result_to_record_out as zero_tare_reading_and_result_to_record_out,
)
from app.deps import AuthContext, get_auth_context
from app.pdf.certificate import generate_certificate_pdf
from app.repositories import instruments as instruments_repo
from app.repositories import profiles as profiles_repo
from app.repositories import readings as readings_repo
from app.repositories import sessions as sessions_repo
from app.repositories import storage as storage_repo
from app.repositories.errors import RepositoryError
from app.services import certificate as certificate_service
from app.services import discrimination as discrimination_service
from app.services import eccentricity as eccentricity_service
from app.services import repeatability as repeatability_service
from app.services import sensitivity as sensitivity_service
from app.services import tilting as tilting_service
from app.services import weighing as weighing_service
from app.services import zero_tare as zero_tare_service
from app.services.sessions import (
    CannotActOnOwnSession,
    CannotIssue,
    InvalidTransition,
    NotAnApprover,
    NotSessionCreator,
    SessionHasNoReadings,
    SessionNotDraft,
    ensure_can_issue,
    ensure_has_readings,
    ensure_is_approver_or_admin,
    ensure_is_creator,
    ensure_not_own_session,
    ensure_session_is_draft,
    ensure_status,
)
from engine.types import VerificationType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_session_or_404(client, session_id: str) -> dict:
    # A RepositoryError here (e.g. a malformed session_id hitting Postgres's
    # "invalid input syntax for type uuid") folds into the same 404 a
    # genuinely nonexistent/not-visible session gets — CLAUDE.md already
    # treats "doesn't exist" and "not visible under RLS" as one bucket, and
    # "can't even resolve as an id" belongs in it too, not a bare crash.
    try:
        row = sessions_repo.get_session(client, session_id)
    except RepositoryError as exc:
        raise HTTPException(status_code=404, detail=f"session not found ({exc.hint})") from exc
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    return row


def _get_instrument_or_404(client, instrument_id: str) -> dict:
    try:
        row = instruments_repo.get_instrument(client, instrument_id)
    except RepositoryError as exc:
        raise HTTPException(status_code=404, detail=f"instrument not found ({exc.hint})") from exc
    if row is None:
        raise HTTPException(status_code=404, detail="instrument not found")
    return row


@router.post("", response_model=SessionOut, status_code=201)
def create_session(payload: SessionIn, auth: AuthContext = Depends(get_auth_context)) -> SessionOut:
    # Confirms the instrument exists and is visible before opening a session
    # against it, rather than deferring to a foreign-key error. payload.instrument_id
    # is a pydantic UUID4 (see contracts/session.py) — stringified for the query builder.
    _get_instrument_or_404(auth.client, str(payload.instrument_id))

    # The two-step insert (session, then its weighing selection row) is the
    # exact path that used to raise a bare IndexError on an empty PostgREST
    # response. Both repo calls now raise RepositoryError instead (never a
    # bare IndexError/APIError) — caught here so the response says which
    # step failed and why, not just "500".
    try:
        session_row = sessions_repo.insert_session(auth.client, auth.user_id, payload)
        sessions_repo.insert_session_test_selection(auth.client, session_row["id"], TestType.WEIGHING.value)
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not create the session ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_row["id"])
    return _build_session_out(auth.client, session_row, selection_rows)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> SessionOut:
    session_row = _get_session_or_404(auth.client, session_id)
    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_id)
    return _build_session_out(auth.client, session_row, selection_rows)


# ---------------------------------------------------------------------------
# Lifecycle transitions: draft -> submitted -> approved -> issued, plus
# returned (approver sends back) and reopen (technician's own way back to
# draft from returned, so readings_write's status='draft' requirement is
# satisfiable again before resubmitting). Separation of duties (CLAUDE.md)
# is enforced twice: RLS's `sessions_update_owner`/`sessions_update_approver`
# policies (db/schema.sql) are the coarse, non-negotiable guard; the explicit
# checks below are the API layer's OWN defense-in-depth, so a rejection is a
# clean, specific error instead of a generic RLS 403.
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_session_out(client, session_row: dict, selection_rows: list[dict]) -> SessionOut:
    """The one place `SessionOut` is assembled from a session row — looks up
    the return reason (audit_log, not a column — see
    app.repositories.sessions.get_latest_return_reason) only when the
    session is actually `returned`, so every other status skips that extra
    read entirely."""
    return_reason = None
    if session_row["status"] == SessionStatus.RETURNED.value:
        return_reason = sessions_repo.get_latest_return_reason(client, session_row["id"])
    return session_out_from_rows(session_row, selection_rows, return_reason=return_reason)


def _update_session_or_error(client, session_id: str, patch: dict) -> dict:
    try:
        return sessions_repo.update_session(client, session_id, patch)
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not update the session ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc


def _log_transition(client, *, session_id: str, actor_id: str, action: str, data: dict) -> None:
    """Non-fatal audit write, same convention as every reading submission
    (docs/architecture.md: "Audit is non-fatal") — with ONE deliberate
    exception: `submit_session`'s `return` action calls its own audit
    insert directly instead, since the return reason has nowhere else to
    live (see `return_session` below)."""
    try:
        readings_repo.insert_audit_log(client, session_id=session_id, actor_id=actor_id, action=action, data=data)
    except Exception as exc:
        logger.warning("audit_log insert failed for session %s (%s): %s", session_id, action, exc)


@router.post("/{session_id}/submit", response_model=SessionOut)
def submit_session(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> SessionOut:
    """Technician moves their own session draft -> submitted. Requires at
    least one recorded reading (across any test) — an empty session has
    nothing for an approver to review."""
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_is_creator(session_row["created_by"], auth.user_id, "submit this session for review")
        ensure_status(SessionStatus(session_row["status"]), SessionStatus.DRAFT, "submit this session for review")
        ensure_has_readings(readings_repo.has_any_reading(auth.client, session_id=session_id))
    except NotSessionCreator as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SessionHasNoReadings as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    updated_row = _update_session_or_error(
        auth.client, session_id, {"status": SessionStatus.SUBMITTED.value, "submitted_at": _now_iso()}
    )
    _log_transition(auth.client, session_id=session_id, actor_id=auth.user_id, action="submitted", data={})

    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_id)
    return _build_session_out(auth.client, updated_row, selection_rows)


@router.post("/{session_id}/reopen", response_model=SessionOut)
def reopen_session(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> SessionOut:
    """Technician moves their own RETURNED session back to draft, so it can
    be edited (readings_write requires status='draft') and resubmitted.
    Not one of the four named transitions in the task brief, but required
    to make "returned -> technician edits -> resubmits" (docs/architecture.md,
    Session lifecycle) actually possible: nothing else moves a session out
    of 'returned'."""
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_is_creator(session_row["created_by"], auth.user_id, "reopen this session for editing")
        ensure_status(SessionStatus(session_row["status"]), SessionStatus.RETURNED, "reopen this session for editing")
    except NotSessionCreator as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    updated_row = _update_session_or_error(auth.client, session_id, {"status": SessionStatus.DRAFT.value})
    _log_transition(auth.client, session_id=session_id, actor_id=auth.user_id, action="reopened", data={})

    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_id)
    return _build_session_out(auth.client, updated_row, selection_rows)


@router.post("/{session_id}/return", response_model=SessionOut)
def return_session(
    session_id: str, payload: SessionReturnIn, auth: AuthContext = Depends(get_auth_context)
) -> SessionOut:
    """Approver/admin moves a SUBMITTED session back to returned, with a
    required reason. Not the session's own creator (separation of duties).

    The audit_log write here is deliberately NOT non-fatal, unlike every
    other transition/reading submission in this app: `data.reason` is the
    ONLY place the reason is stored (no `test_sessions` column exists for
    it — see app.contracts.session.SessionOut.return_reason), so losing that
    write would silently lose the reason while still reporting success.
    Written BEFORE the status update for the same reason: if the audit
    write fails, nothing has changed yet (safe to retry); if the status
    update then fails, the audit trail still has the reason (a resubmitted
    return call is a second, harmless append-only row).
    """
    session_row = _get_session_or_404(auth.client, session_id)
    role = profiles_repo.get_role(auth.client, auth.user_id)

    try:
        ensure_is_approver_or_admin(role, "return this session")
        ensure_not_own_session(session_row["created_by"], auth.user_id, "return")
        ensure_status(SessionStatus(session_row["status"]), SessionStatus.SUBMITTED, "return this session")
    except NotAnApprover as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CannotActOnOwnSession as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        readings_repo.insert_audit_log(
            auth.client,
            session_id=session_id,
            actor_id=auth.user_id,
            action="returned",
            data={"reason": payload.reason},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="could not record the return reason; the session was not returned — please retry",
        ) from exc

    updated_row = _update_session_or_error(auth.client, session_id, {"status": SessionStatus.RETURNED.value})

    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_id)
    return _build_session_out(auth.client, updated_row, selection_rows)


@router.post("/{session_id}/approve", response_model=SessionOut)
def approve_session(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> SessionOut:
    """Approver/admin moves a SUBMITTED session to approved. Not the
    session's own creator (separation of duties) — the core guarantee this
    whole task exists to demonstrate."""
    session_row = _get_session_or_404(auth.client, session_id)
    role = profiles_repo.get_role(auth.client, auth.user_id)

    try:
        ensure_is_approver_or_admin(role, "approve this session")
        ensure_not_own_session(session_row["created_by"], auth.user_id, "approve")
        ensure_status(SessionStatus(session_row["status"]), SessionStatus.SUBMITTED, "approve this session")
    except NotAnApprover as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CannotActOnOwnSession as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    updated_row = _update_session_or_error(
        auth.client,
        session_id,
        {"status": SessionStatus.APPROVED.value, "approved_by": auth.user_id, "approved_at": _now_iso()},
    )
    _log_transition(auth.client, session_id=session_id, actor_id=auth.user_id, action="approved", data={})

    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_id)
    return _build_session_out(auth.client, updated_row, selection_rows)


@router.post("/{session_id}/issue", response_model=SessionOut)
def issue_session(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> SessionOut:
    """Approver/admin moves an APPROVED session to issued, assigning the
    certificate number from `certificate_number_seq` (never before this
    point — CLAUDE.md). Who may issue: an admin, or specifically the SAME
    approver who approved it (`ensure_can_issue`) — a deliberate, documented
    choice (docs/architecture.md, Session lifecycle), not something RLS
    itself distinguishes.
    """
    session_row = _get_session_or_404(auth.client, session_id)
    role = profiles_repo.get_role(auth.client, auth.user_id)

    try:
        ensure_is_approver_or_admin(role, "issue this session's certificate")
        ensure_not_own_session(session_row["created_by"], auth.user_id, "issue this session's certificate for")
        ensure_status(SessionStatus(session_row["status"]), SessionStatus.APPROVED, "issue this session's certificate")
        ensure_can_issue(role, auth.user_id, session_row.get("approved_by"))
    except NotAnApprover as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CannotActOnOwnSession as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CannotIssue as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        certificate_number = sessions_repo.issue_certificate_number(auth.client)
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not generate a certificate number ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    updated_row = _update_session_or_error(
        auth.client,
        session_id,
        {
            "status": SessionStatus.ISSUED.value,
            "issued_at": _now_iso(),
            "certificate_number": certificate_number,
        },
    )
    _log_transition(
        auth.client,
        session_id=session_id,
        actor_id=auth.user_id,
        action="issued",
        data={"certificate_number": certificate_number},
    )

    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_id)
    return _build_session_out(auth.client, updated_row, selection_rows)


@router.get("/{session_id}/weighing/sequence", response_model=list[WeighingSequenceEntryOut])
def get_weighing_sequence(
    session_id: str, auth: AuthContext = Depends(get_auth_context)
) -> list[WeighingSequenceEntryOut]:
    session_row = _get_session_or_404(auth.client, session_id)
    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)

    sequence = weighing_service.build_sequence(instrument, VerificationType(session_row["verification_type"]))
    return [
        WeighingSequenceEntryOut(sequence_no=i, L=entry.L, m=entry.m, kind=entry.kind, mpe=entry.mpe)
        for i, entry in enumerate(sequence)
    ]


@router.get("/{session_id}/weighing/readings", response_model=list[WeighingReadingRecordOut])
def list_weighing_readings(
    session_id: str, auth: AuthContext = Depends(get_auth_context)
) -> list[WeighingReadingRecordOut]:
    """Read-only: every submitted Weighing reading for this session paired
    with its computed result, so the client can reconstruct the R76-2 form
    table on load — closing the "refresh loses progress" gap
    (docs/architecture.md known-gaps). RLS-scoped like every other route:
    creator + approver/admin see it, per the existing readings/results
    select policies — no new policy needed, no schema change.
    """
    _get_session_or_404(auth.client, session_id)  # visibility check only

    reading_rows = readings_repo.list_readings(auth.client, session_id=session_id, test_type=TestType.WEIGHING.value)
    result_rows = readings_repo.list_results(auth.client, session_id=session_id, test_type=TestType.WEIGHING.value)
    results_by_reading_id = {row["reading_id"]: row for row in result_rows if row.get("reading_id")}

    # There's no update endpoint (docs/architecture.md) — resubmitting a
    # direction inserts a second reading rather than overwriting the first.
    # reading_rows is ordered by created_at, so this dict comprehension's
    # last-write-wins semantics keep only the latest submission per
    # (sequence_no, direction), matching what the form should actually show.
    latest_by_key = {
        (reading_row["sequence_no"], reading_row["direction"]): (reading_row, results_by_reading_id[reading_row["id"]])
        for reading_row in reading_rows
        if reading_row["id"] in results_by_reading_id
    }

    records = [reading_and_result_to_record_out(reading_row, result_row) for reading_row, result_row in latest_by_key.values()]
    records.sort(key=lambda record: (record.sequence_no, record.direction.value))
    return records


@router.post("/{session_id}/weighing/readings", response_model=WeighingResultOut, status_code=201)
def submit_weighing_reading(
    session_id: str,
    payload: WeighingReadingSubmitIn,
    auth: AuthContext = Depends(get_auth_context),
) -> WeighingResultOut:
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_session_is_draft(SessionStatus(session_row["status"]))
    except SessionNotDraft as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])

    try:
        submission = weighing_service.compute_result_for_submission(payload, instrument, verification_type)
    except weighing_service.SequenceNumberOutOfRange as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Write reading + result together. supabase-py/PostgREST has no
    # multi-table client-side transaction (see docs/architecture.md) — insert
    # reading, then result; on result-insert failure, delete the orphan
    # reading rather than leave a reading with no computed verdict. A
    # single Postgres RPC doing both inserts atomically would remove this
    # rollback step entirely; not built in this task.
    try:
        reading_row = readings_repo.insert_reading(
            auth.client,
            session_id=session_id,
            entered_by=auth.user_id,
            test_type=TestType.WEIGHING.value,
            sequence_no=payload.sequence_no,
            direction=payload.direction.value,
            data=submission.reading.model_dump(mode="json"),
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not record the reading ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    try:
        readings_repo.insert_result(
            auth.client,
            session_id=session_id,
            test_type=TestType.WEIGHING.value,
            reading_id=reading_row["id"],
            result=submission.result_out.model_dump(mode="json"),
            passed=submission.result_out.passed,
        )
    except RepositoryError as exc:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"failed to record the computed result ({exc.hint}); the reading was rolled back",
        ) from exc
    except Exception:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=500,
            detail="failed to record the computed result; the reading was rolled back",
        ) from None

    # Audit write is non-fatal: log a warning and still return success on
    # failure (docs/plan.md: "audit writes non-fatal but surfaced").
    try:
        readings_repo.insert_audit_log(
            auth.client,
            session_id=session_id,
            actor_id=auth.user_id,
            action="weighing_reading_submitted",
            data={"sequence_no": payload.sequence_no, "passed": submission.result_out.passed},
        )
    except Exception as exc:
        logger.warning("audit_log insert failed for session %s: %s", session_id, exc)

    return submission.result_out


# ---------------------------------------------------------------------------
# Zero/tare device accuracy — a Weighing variant (test_type='weighing', no
# own test_type in db/schema.sql). Distinguished from a regular Weighing
# load-sequence reading by `direction`: always set for the latter, always
# null for a zero/tare reading. See app/contracts/zero_tare.py.
# ---------------------------------------------------------------------------


@router.get("/{session_id}/zero-tare/checks", response_model=list[ZeroTareCheckOut])
def get_zero_tare_checks(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> list[ZeroTareCheckOut]:
    session_row = _get_session_or_404(auth.client, session_id)
    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])
    return zero_tare_service.checks_with_mpe(instrument, verification_type)


@router.get("/{session_id}/zero-tare/readings", response_model=list[ZeroTareReadingRecordOut])
def list_zero_tare_readings(
    session_id: str, auth: AuthContext = Depends(get_auth_context)
) -> list[ZeroTareReadingRecordOut]:
    _get_session_or_404(auth.client, session_id)  # visibility check only

    reading_rows = readings_repo.list_readings(auth.client, session_id=session_id, test_type=TestType.WEIGHING.value)
    reading_rows = [row for row in reading_rows if row.get("direction") is None]
    result_rows = readings_repo.list_results(auth.client, session_id=session_id, test_type=TestType.WEIGHING.value)
    results_by_reading_id = {row["reading_id"]: row for row in result_rows if row.get("reading_id")}

    latest_by_sequence_no = {
        reading_row["sequence_no"]: (reading_row, results_by_reading_id[reading_row["id"]])
        for reading_row in reading_rows
        if reading_row["id"] in results_by_reading_id
    }

    records = [zero_tare_reading_and_result_to_record_out(r, res) for r, res in latest_by_sequence_no.values()]
    records.sort(key=lambda record: record.sequence_no)
    return records


@router.post("/{session_id}/zero-tare/readings", response_model=ZeroTareResultOut, status_code=201)
def submit_zero_tare_reading(
    session_id: str,
    payload: ZeroTareReadingSubmitIn,
    auth: AuthContext = Depends(get_auth_context),
) -> ZeroTareResultOut:
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_session_is_draft(SessionStatus(session_row["status"]))
    except SessionNotDraft as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])

    try:
        submission = zero_tare_service.compute_result_for_submission(payload, instrument, verification_type)
    except zero_tare_service.SequenceNumberOutOfRange as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        reading_row = readings_repo.insert_reading(
            auth.client,
            session_id=session_id,
            entered_by=auth.user_id,
            test_type=TestType.WEIGHING.value,
            sequence_no=payload.sequence_no,
            direction=None,
            data=submission.reading.model_dump(mode="json"),
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not record the reading ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    try:
        readings_repo.insert_result(
            auth.client,
            session_id=session_id,
            test_type=TestType.WEIGHING.value,
            reading_id=reading_row["id"],
            result=submission.result_out.model_dump(mode="json"),
            passed=submission.result_out.passed,
        )
    except RepositoryError as exc:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"failed to record the computed result ({exc.hint}); the reading was rolled back",
        ) from exc
    except Exception:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=500,
            detail="failed to record the computed result; the reading was rolled back",
        ) from None

    try:
        readings_repo.insert_audit_log(
            auth.client,
            session_id=session_id,
            actor_id=auth.user_id,
            action="zero_tare_reading_submitted",
            data={"sequence_no": payload.sequence_no, "passed": submission.result_out.passed},
        )
    except Exception as exc:
        logger.warning("audit_log insert failed for session %s: %s", session_id, exc)

    return submission.result_out


# ---------------------------------------------------------------------------
# Repeatability — two independent 10-reading series at fixed loads, no E0,
# a series' verdict a property of the whole series (spread), not any single
# reading. See app/services/repeatability.py.
# ---------------------------------------------------------------------------


def _repeatability_stored_readings(client, session_id: str, series_no: int) -> list[tuple[int, Decimal, Decimal]]:
    """Fetch + dedupe-to-latest this series' readings as (sequence_no, I,
    delta_l) tuples — the shape app.services.repeatability.compute_series
    expects. Same last-write-wins convention as Weighing's readings GET
    (list_readings is ordered by created_at, so a later dict-write for the
    same sequence_no wins)."""
    reading_rows = readings_repo.list_readings(client, session_id=session_id, test_type=TestType.REPEATABILITY.value)
    reading_rows = [row for row in reading_rows if row["series_no"] == series_no]
    latest_by_sequence_no = {row["sequence_no"]: row for row in reading_rows}
    return [
        (row["sequence_no"], Decimal(row["data"]["I"]), Decimal(row["data"]["delta_l"]))
        for row in latest_by_sequence_no.values()
    ]


@router.get("/{session_id}/repeatability/readings", response_model=list[RepeatabilitySeriesOut])
def list_repeatability_readings(
    session_id: str, auth: AuthContext = Depends(get_auth_context)
) -> list[RepeatabilitySeriesOut]:
    session_row = _get_session_or_404(auth.client, session_id)
    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])

    return [
        repeatability_service.compute_series(
            instrument, verification_type, series_no, _repeatability_stored_readings(auth.client, session_id, series_no)
        )
        for series_no in (1, 2)
    ]


@router.post("/{session_id}/repeatability/readings", response_model=RepeatabilitySeriesOut, status_code=201)
def submit_repeatability_reading(
    session_id: str,
    payload: RepeatabilityReadingSubmitIn,
    auth: AuthContext = Depends(get_auth_context),
) -> RepeatabilitySeriesOut:
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_session_is_draft(SessionStatus(session_row["status"]))
    except SessionNotDraft as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])

    existing = _repeatability_stored_readings(auth.client, session_id, payload.series_no)
    submission = repeatability_service.compute_result_for_submission(payload, instrument, verification_type, existing)

    try:
        reading_row = readings_repo.insert_reading(
            auth.client,
            session_id=session_id,
            entered_by=auth.user_id,
            test_type=TestType.REPEATABILITY.value,
            sequence_no=payload.sequence_no,
            series_no=payload.series_no,
            data={"I": str(payload.I), "delta_l": str(payload.delta_l)},
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not record the reading ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    try:
        readings_repo.insert_result(
            auth.client,
            session_id=session_id,
            test_type=TestType.REPEATABILITY.value,
            reading_id=reading_row["id"],
            result={"E": str(submission.this_reading_E), "within_mpe": submission.this_reading_within_mpe},
            passed=submission.this_reading_within_mpe,
        )
    except RepositoryError as exc:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"failed to record the computed result ({exc.hint}); the reading was rolled back",
        ) from exc
    except Exception:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=500,
            detail="failed to record the computed result; the reading was rolled back",
        ) from None

    try:
        readings_repo.insert_audit_log(
            auth.client,
            session_id=session_id,
            actor_id=auth.user_id,
            action="repeatability_reading_submitted",
            data={
                "series_no": payload.series_no,
                "sequence_no": payload.sequence_no,
                "within_mpe": submission.this_reading_within_mpe,
            },
        )
    except Exception as exc:
        logger.warning("audit_log insert failed for session %s: %s", session_id, exc)

    return submission.series_out


# ---------------------------------------------------------------------------
# Eccentricity — 4 independent receptor positions, each with its OWN E0
# (re-measured before each position). See app/services/eccentricity.py.
# ---------------------------------------------------------------------------


def _eccentricity_stored_records(client, session_id: str) -> dict[int, EccentricityReadingRecordOut]:
    reading_rows = readings_repo.list_readings(client, session_id=session_id, test_type=TestType.ECCENTRICITY.value)
    result_rows = readings_repo.list_results(client, session_id=session_id, test_type=TestType.ECCENTRICITY.value)
    results_by_reading_id = {row["reading_id"]: row for row in result_rows if row.get("reading_id")}

    latest_by_position: dict[int, tuple[dict, dict]] = {}
    for row in reading_rows:  # ordered by created_at -> last write wins
        if row["id"] in results_by_reading_id:
            latest_by_position[row["position_no"]] = (row, results_by_reading_id[row["id"]])

    return {
        position_no: eccentricity_reading_and_result_to_record_out(reading_row, result_row)
        for position_no, (reading_row, result_row) in latest_by_position.items()
    }


@router.get("/{session_id}/eccentricity/setup", response_model=EccentricitySetupOut)
def get_eccentricity_setup(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> EccentricitySetupOut:
    session_row = _get_session_or_404(auth.client, session_id)
    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])
    return eccentricity_service.setup_out(instrument, verification_type)


@router.get("/{session_id}/eccentricity/readings", response_model=list[EccentricityReadingRecordOut])
def list_eccentricity_readings(
    session_id: str, auth: AuthContext = Depends(get_auth_context)
) -> list[EccentricityReadingRecordOut]:
    _get_session_or_404(auth.client, session_id)  # visibility check only
    records = list(_eccentricity_stored_records(auth.client, session_id).values())
    records.sort(key=lambda record: record.position_no)
    return records


@router.post("/{session_id}/eccentricity/readings", response_model=EccentricityResultOut, status_code=201)
def submit_eccentricity_reading(
    session_id: str,
    payload: EccentricityReadingSubmitIn,
    auth: AuthContext = Depends(get_auth_context),
) -> EccentricityResultOut:
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_session_is_draft(SessionStatus(session_row["status"]))
    except SessionNotDraft as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])

    submission = eccentricity_service.compute_result_for_submission(payload, instrument, verification_type)

    try:
        reading_row = readings_repo.insert_reading(
            auth.client,
            session_id=session_id,
            entered_by=auth.user_id,
            test_type=TestType.ECCENTRICITY.value,
            sequence_no=payload.position_no,
            position_no=payload.position_no,
            data=submission.reading.model_dump(mode="json"),
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not record the reading ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    try:
        readings_repo.insert_result(
            auth.client,
            session_id=session_id,
            test_type=TestType.ECCENTRICITY.value,
            reading_id=reading_row["id"],
            result=submission.result_out.model_dump(mode="json"),
            passed=submission.result_out.passed,
        )
    except RepositoryError as exc:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"failed to record the computed result ({exc.hint}); the reading was rolled back",
        ) from exc
    except Exception:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=500,
            detail="failed to record the computed result; the reading was rolled back",
        ) from None

    try:
        readings_repo.insert_audit_log(
            auth.client,
            session_id=session_id,
            actor_id=auth.user_id,
            action="eccentricity_reading_submitted",
            data={"position_no": payload.position_no, "passed": submission.result_out.passed},
        )
    except Exception as exc:
        logger.warning("audit_log insert failed for session %s: %s", session_id, exc)

    return submission.result_out


# ---------------------------------------------------------------------------
# Discrimination — THREE distinct sub-procedures (analog/non-self-indicating/
# digital), the applicable one DERIVED from the instrument's own
# indication_type, never a client-submitted flag. See
# app/services/discrimination.py.
# ---------------------------------------------------------------------------


@router.get("/{session_id}/discrimination/checks", response_model=list[DiscriminationCheckOut])
def get_discrimination_checks(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> list[DiscriminationCheckOut]:
    session_row = _get_session_or_404(auth.client, session_id)
    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])
    return discrimination_service.checks_with_mpe(instrument, verification_type)


@router.get("/{session_id}/discrimination/readings", response_model=list[DiscriminationReadingRecordOut])
def list_discrimination_readings(
    session_id: str, auth: AuthContext = Depends(get_auth_context)
) -> list[DiscriminationReadingRecordOut]:
    _get_session_or_404(auth.client, session_id)  # visibility check only

    reading_rows = readings_repo.list_readings(auth.client, session_id=session_id, test_type=TestType.DISCRIMINATION.value)
    result_rows = readings_repo.list_results(auth.client, session_id=session_id, test_type=TestType.DISCRIMINATION.value)
    results_by_reading_id = {row["reading_id"]: row for row in result_rows if row.get("reading_id")}

    latest_by_sequence_no = {
        reading_row["sequence_no"]: (reading_row, results_by_reading_id[reading_row["id"]])
        for reading_row in reading_rows
        if reading_row["id"] in results_by_reading_id
    }

    records = [discrimination_reading_and_result_to_record_out(r, res) for r, res in latest_by_sequence_no.values()]
    records.sort(key=lambda record: record.sequence_no)
    return records


@router.post("/{session_id}/discrimination/readings", response_model=DiscriminationResultOut, status_code=201)
def submit_discrimination_reading(
    session_id: str,
    payload: DiscriminationReadingSubmitIn,
    auth: AuthContext = Depends(get_auth_context),
) -> DiscriminationResultOut:
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_session_is_draft(SessionStatus(session_row["status"]))
    except SessionNotDraft as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])

    try:
        submission = discrimination_service.compute_result_for_submission(payload, instrument, verification_type)
    except discrimination_service.SequenceNumberOutOfRange as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except discrimination_service.MissingFieldsForVariant as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        reading_row = readings_repo.insert_reading(
            auth.client,
            session_id=session_id,
            entered_by=auth.user_id,
            test_type=TestType.DISCRIMINATION.value,
            sequence_no=payload.sequence_no,
            data=submission.reading_data,
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not record the reading ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    try:
        readings_repo.insert_result(
            auth.client,
            session_id=session_id,
            test_type=TestType.DISCRIMINATION.value,
            reading_id=reading_row["id"],
            result=submission.result_out.model_dump(mode="json"),
            passed=submission.result_out.passed,
        )
    except RepositoryError as exc:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"failed to record the computed result ({exc.hint}); the reading was rolled back",
        ) from exc
    except Exception:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=500,
            detail="failed to record the computed result; the reading was rolled back",
        ) from None

    try:
        readings_repo.insert_audit_log(
            auth.client,
            session_id=session_id,
            actor_id=auth.user_id,
            action="discrimination_reading_submitted",
            data={"sequence_no": payload.sequence_no, "variant": submission.variant, "passed": submission.result_out.passed},
        )
    except Exception as exc:
        logger.warning("audit_log insert failed for session %s: %s", session_id, exc)

    return submission.result_out


# ---------------------------------------------------------------------------
# Sensitivity — non-self-indicating instruments only (clause 6.1); pass
# threshold tiered by accuracy class AND Max. See
# app/services/sensitivity.py.
# ---------------------------------------------------------------------------


@router.get("/{session_id}/sensitivity/checks", response_model=list[SensitivityCheckOut])
def get_sensitivity_checks(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> list[SensitivityCheckOut]:
    session_row = _get_session_or_404(auth.client, session_id)
    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])
    return sensitivity_service.checks_with_mpe(instrument, verification_type)


@router.get("/{session_id}/sensitivity/readings", response_model=list[SensitivityReadingRecordOut])
def list_sensitivity_readings(
    session_id: str, auth: AuthContext = Depends(get_auth_context)
) -> list[SensitivityReadingRecordOut]:
    _get_session_or_404(auth.client, session_id)  # visibility check only

    reading_rows = readings_repo.list_readings(auth.client, session_id=session_id, test_type=TestType.SENSITIVITY.value)
    result_rows = readings_repo.list_results(auth.client, session_id=session_id, test_type=TestType.SENSITIVITY.value)
    results_by_reading_id = {row["reading_id"]: row for row in result_rows if row.get("reading_id")}

    latest_by_sequence_no = {
        reading_row["sequence_no"]: (reading_row, results_by_reading_id[reading_row["id"]])
        for reading_row in reading_rows
        if reading_row["id"] in results_by_reading_id
    }

    records = [sensitivity_reading_and_result_to_record_out(r, res) for r, res in latest_by_sequence_no.values()]
    records.sort(key=lambda record: record.sequence_no)
    return records


@router.post("/{session_id}/sensitivity/readings", response_model=SensitivityResultOut, status_code=201)
def submit_sensitivity_reading(
    session_id: str,
    payload: SensitivityReadingSubmitIn,
    auth: AuthContext = Depends(get_auth_context),
) -> SensitivityResultOut:
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_session_is_draft(SessionStatus(session_row["status"]))
    except SessionNotDraft as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    if instrument.indication_type is not IndicationType.NON_SELF_INDICATING:
        raise HTTPException(status_code=422, detail="Sensitivity applies only to non-self-indicating instruments")
    verification_type = VerificationType(session_row["verification_type"])

    try:
        submission = sensitivity_service.compute_result_for_submission(payload, instrument, verification_type)
    except sensitivity_service.SequenceNumberOutOfRange as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        reading_row = readings_repo.insert_reading(
            auth.client,
            session_id=session_id,
            entered_by=auth.user_id,
            test_type=TestType.SENSITIVITY.value,
            sequence_no=payload.sequence_no,
            data={"permanent_displacement_mm": str(payload.permanent_displacement_mm)},
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not record the reading ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    try:
        readings_repo.insert_result(
            auth.client,
            session_id=session_id,
            test_type=TestType.SENSITIVITY.value,
            reading_id=reading_row["id"],
            result=submission.result_out.model_dump(mode="json"),
            passed=submission.result_out.passed,
        )
    except RepositoryError as exc:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"failed to record the computed result ({exc.hint}); the reading was rolled back",
        ) from exc
    except Exception:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=500,
            detail="failed to record the computed result; the reading was rolled back",
        ) from None

    try:
        readings_repo.insert_audit_log(
            auth.client,
            session_id=session_id,
            actor_id=auth.user_id,
            action="sensitivity_reading_submitted",
            data={"sequence_no": payload.sequence_no, "passed": submission.result_out.passed},
        )
    except Exception as exc:
        logger.warning("audit_log insert failed for session %s: %s", session_id, exc)

    return submission.result_out


# ---------------------------------------------------------------------------
# Tilting — mobile instruments only (clause 4.18); the minimal 8.3.3/4.18
# slice (reference + 4 tilted positions x unloaded/mid-load/Max), whole-set
# pass criteria recomputed on every GET/POST. `sequence_no` encodes the
# phase (0=unloaded, 1=loaded_l, 2=loaded_max); `position_no` is the tilt
# position (1-5). See app/services/tilting.py.
# ---------------------------------------------------------------------------

_TILT_PHASE_TO_SEQUENCE_NO = {"unloaded": 0, "loaded_l": 1, "loaded_max": 2}
_TILT_SEQUENCE_NO_TO_PHASE = {v: k for k, v in _TILT_PHASE_TO_SEQUENCE_NO.items()}


def _tilting_stored_readings(client, session_id: str) -> list[tuple]:
    """Fetch + dedupe-to-latest (per phase, position_no) Tilting readings as
    (phase, position_no, I, delta_l) tuples — the shape
    app.services.tilting.compute_state expects."""
    reading_rows = readings_repo.list_readings(client, session_id=session_id, test_type=TestType.TILTING.value)
    latest_by_key = {}
    for row in reading_rows:  # ordered by created_at -> last write wins
        latest_by_key[(row["sequence_no"], row["position_no"])] = row
    return [
        (_TILT_SEQUENCE_NO_TO_PHASE[row["sequence_no"]], row["position_no"], Decimal(row["data"]["I"]), Decimal(row["data"]["delta_l"]))
        for row in latest_by_key.values()
    ]


@router.get("/{session_id}/tilting/readings", response_model=TiltingStateOut)
def get_tilting_state(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> TiltingStateOut:
    session_row = _get_session_or_404(auth.client, session_id)
    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])
    stored = _tilting_stored_readings(auth.client, session_id)
    return tilting_service.compute_state(instrument, verification_type, stored)


@router.post("/{session_id}/tilting/readings", response_model=TiltingStateOut, status_code=201)
def submit_tilting_reading(
    session_id: str,
    payload: TiltingReadingSubmitIn,
    auth: AuthContext = Depends(get_auth_context),
) -> TiltingStateOut:
    session_row = _get_session_or_404(auth.client, session_id)

    try:
        ensure_session_is_draft(SessionStatus(session_row["status"]))
    except SessionNotDraft as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    instrument = instrument_params_from_row(instrument_row)
    if not instrument.is_mobile:
        raise HTTPException(status_code=422, detail="Tilting applies only to mobile instruments")
    verification_type = VerificationType(session_row["verification_type"])

    # Fetch what's already stored BEFORE inserting, then merge the new
    # submission into that list locally (last-write-wins on the same
    # (phase, position_no), same convention as everywhere else) rather than
    # re-fetching after the insert — this can't disagree with itself over
    # read-after-write timing, and matches Repeatability's own router
    # pattern exactly.
    existing = _tilting_stored_readings(auth.client, session_id)
    merged = {(phase, position_no): (I, delta_l) for phase, position_no, I, delta_l in existing}
    merged[(payload.phase, payload.position_no)] = (payload.I, payload.delta_l)
    stored = [(phase, position_no, I, delta_l) for (phase, position_no), (I, delta_l) in merged.items()]

    state = tilting_service.compute_state(instrument, verification_type, stored)
    this_row = next((r for r in state.readings if r.phase == payload.phase and r.position_no == payload.position_no), None)

    try:
        reading_row = readings_repo.insert_reading(
            auth.client,
            session_id=session_id,
            entered_by=auth.user_id,
            test_type=TestType.TILTING.value,
            sequence_no=_TILT_PHASE_TO_SEQUENCE_NO[payload.phase],
            position_no=payload.position_no,
            data={"I": str(payload.I), "delta_l": str(payload.delta_l)},
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not record the reading ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc

    try:
        readings_repo.insert_result(
            auth.client,
            session_id=session_id,
            test_type=TestType.TILTING.value,
            reading_id=reading_row["id"],
            result={"E": str(this_row.E) if this_row else None, "Ec": str(this_row.Ec) if this_row and this_row.Ec is not None else None},
            passed=None,
        )
    except RepositoryError as exc:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"failed to record the computed result ({exc.hint}); the reading was rolled back",
        ) from exc
    except Exception:
        readings_repo.delete_reading(auth.client, reading_row["id"])
        raise HTTPException(
            status_code=500,
            detail="failed to record the computed result; the reading was rolled back",
        ) from None

    try:
        readings_repo.insert_audit_log(
            auth.client,
            session_id=session_id,
            actor_id=auth.user_id,
            action="tilting_reading_submitted",
            data={"phase": payload.phase, "position_no": payload.position_no},
        )
    except Exception as exc:
        logger.warning("audit_log insert failed for session %s: %s", session_id, exc)

    return state


# ---------------------------------------------------------------------------
# Certificate PDF generation (Part A) — an issued session's report, stored
# in Supabase Storage (never local disk, CLAUDE.md) and returned directly
# so the caller has an immediate download. See app/services/certificate.py
# and app/pdf/certificate.py for the data-assembly/rendering split.
# ---------------------------------------------------------------------------

_OTHER_TEST_LABELS = {
    "zero_tare": "Zero/tare device accuracy",
    "repeatability": "Repeatability",
    "eccentricity": "Eccentricity (3.1 weights)",
    "discrimination": "Discrimination",
    "sensitivity": "Sensitivity",
    "tilting": "Tilting",
}


def _verify_url(request: Request, certificate_number: str) -> str:
    override = os.environ.get("PUBLIC_APP_BASE_URL")
    base = override or str(request.base_url)
    return f"{base.rstrip('/')}/verify/{certificate_number}"


def _build_certificate_data(client, session_row: dict, instrument_row: dict) -> certificate_service.CertificateData:
    instrument = instrument_out_from_row(instrument_row)
    instrument_params = instrument_params_from_row(instrument_row)
    verification_type = VerificationType(session_row["verification_type"])
    session_id = session_row["id"]

    weighing_reading_rows = readings_repo.list_readings(client, session_id=session_id, test_type=TestType.WEIGHING.value)
    weighing_result_rows = readings_repo.list_results(client, session_id=session_id, test_type=TestType.WEIGHING.value)
    weighing_rows = certificate_service.weighing_rows_from_db(weighing_reading_rows, weighing_result_rows)
    overall_weighing = certificate_service.weighing_overall_passed(weighing_rows)

    # Zero/tare: the SAME weighing rows, but only the ones with direction
    # IS null (docs/architecture.md) — a distinct sub-procedure with its
    # own independent per-check verdicts, summarized rather than tabulated.
    zero_tare_reading_ids = {row["id"] for row in weighing_reading_rows if row.get("direction") is None}
    zero_tare_passed = [
        row["passed"] for row in weighing_result_rows if row.get("reading_id") in zero_tare_reading_ids
    ]
    zero_tare_summary = certificate_service.simple_passed_summary(
        _OTHER_TEST_LABELS["zero_tare"], zero_tare_passed
    )

    eccentricity_passed = [
        row["passed"]
        for row in readings_repo.list_results(client, session_id=session_id, test_type=TestType.ECCENTRICITY.value)
    ]
    eccentricity_summary = certificate_service.simple_passed_summary(
        _OTHER_TEST_LABELS["eccentricity"], eccentricity_passed
    )

    discrimination_passed = [
        row["passed"]
        for row in readings_repo.list_results(client, session_id=session_id, test_type=TestType.DISCRIMINATION.value)
    ]
    discrimination_summary = certificate_service.simple_passed_summary(
        _OTHER_TEST_LABELS["discrimination"], discrimination_passed
    )

    sensitivity_passed = [
        row["passed"]
        for row in readings_repo.list_results(client, session_id=session_id, test_type=TestType.SENSITIVITY.value)
    ]
    sensitivity_summary = certificate_service.simple_passed_summary(
        _OTHER_TEST_LABELS["sensitivity"], sensitivity_passed
    )

    # Repeatability/Tilting need their OWN aggregate logic (mpe+spread;
    # whole-dataset criteria) — recomputed via the exact same service
    # functions their own GET routes call, not a naive per-reading scan.
    repeatability_series = [
        repeatability_service.compute_series(
            instrument_params, verification_type, series_no, _repeatability_stored_readings(client, session_id, series_no)
        )
        for series_no in (1, 2)
    ]
    repeatability_summary = certificate_service.series_aggregate_summary(
        _OTHER_TEST_LABELS["repeatability"], repeatability_series
    )

    tilting_state = tilting_service.compute_state(
        instrument_params, verification_type, _tilting_stored_readings(client, session_id)
    )
    tilting_summary = certificate_service.state_summary(_OTHER_TEST_LABELS["tilting"], tilting_state)

    return certificate_service.CertificateData(
        certificate_number=session_row["certificate_number"],
        verification_type=verification_type.value,
        issued_at=session_row.get("issued_at"),
        approved_at=session_row.get("approved_at"),
        instrument=instrument,
        weighing_rows=weighing_rows,
        weighing_overall_passed=overall_weighing,
        other_tests=[
            zero_tare_summary,
            repeatability_summary,
            eccentricity_summary,
            discrimination_summary,
            tilting_summary,
            sensitivity_summary,
        ],
    )


@router.post("/{session_id}/report")
def generate_session_report(
    session_id: str, request: Request, auth: AuthContext = Depends(get_auth_context)
) -> Response:
    """Generates the certificate PDF for an ISSUED session, stores it in
    Supabase Storage, and returns the PDF bytes directly — approver/admin
    or the session's own creator only (item 1's authorization is
    deliberately broader than the lifecycle-transition endpoints above:
    generating a copy of your OWN already-issued certificate is not a
    separation-of-duties-sensitive action)."""
    session_row = _get_session_or_404(auth.client, session_id)

    role = profiles_repo.get_role(auth.client, auth.user_id)
    is_creator = auth.user_id == session_row["created_by"]
    is_approver_or_admin = role in ("approver", "admin")
    if not (is_creator or is_approver_or_admin):
        raise HTTPException(
            status_code=403,
            detail="only the session's creator, an approver, or an admin may generate this report",
        )

    try:
        ensure_status(SessionStatus(session_row["status"]), SessionStatus.ISSUED, "generate this session's certificate report")
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    instrument_row = _get_instrument_or_404(auth.client, session_row["instrument_id"])
    data = _build_certificate_data(auth.client, session_row, instrument_row)
    verify_url = _verify_url(request, session_row["certificate_number"])
    pdf_bytes = generate_certificate_pdf(data, verify_url)

    storage_path = f"certificates/{session_row['certificate_number']}.pdf"
    try:
        storage_repo.upload_report_pdf(auth.client, path=storage_path, pdf_bytes=pdf_bytes)
    except storage_repo.StorageError as exc:
        raise HTTPException(status_code=500, detail=f"could not store the generated certificate: {exc}") from exc

    # Non-fatal: `storage_path` is fully deterministic from
    # `certificate_number` alone, so even if this bookkeeping write fails,
    # the PDF itself is already safely stored and already in hand — unlike
    # a return-reason, nothing here is lost if this one call fails.
    try:
        sessions_repo.set_report_storage_path(auth.client, session_id, storage_path)
    except RepositoryError as exc:
        logger.warning("could not record report_storage_path for session %s: %s", session_id, exc)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{session_row["certificate_number"]}.pdf"'},
    )
