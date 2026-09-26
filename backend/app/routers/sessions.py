import logging

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.common import SessionStatus, TestType
from app.contracts.instrument import instrument_params_from_row
from app.contracts.session import SessionIn, SessionOut, session_out_from_rows
from app.contracts.weighing import WeighingReadingSubmitIn, WeighingResultOut, WeighingSequenceEntryOut
from app.deps import AuthContext, get_auth_context
from app.repositories import instruments as instruments_repo
from app.repositories import readings as readings_repo
from app.repositories import sessions as sessions_repo
from app.services import weighing as weighing_service
from app.services.sessions import SessionNotDraft, ensure_session_is_draft
from engine.types import VerificationType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_session_or_404(client, session_id: str) -> dict:
    row = sessions_repo.get_session(client, session_id)
    if row is None:
        # Same not-found/not-visible non-distinction as instruments — see
        # routers/instruments.py.
        raise HTTPException(status_code=404, detail="session not found")
    return row


def _get_instrument_or_404(client, instrument_id: str) -> dict:
    row = instruments_repo.get_instrument(client, instrument_id)
    if row is None:
        raise HTTPException(status_code=404, detail="instrument not found")
    return row


@router.post("", response_model=SessionOut, status_code=201)
def create_session(payload: SessionIn, auth: AuthContext = Depends(get_auth_context)) -> SessionOut:
    # Confirms the instrument exists and is visible before opening a session
    # against it, rather than deferring to a foreign-key error.
    _get_instrument_or_404(auth.client, payload.instrument_id)

    session_row = sessions_repo.insert_session(auth.client, auth.user_id, payload)
    sessions_repo.insert_session_test_selection(auth.client, session_row["id"], TestType.WEIGHING.value)
    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_row["id"])
    return session_out_from_rows(session_row, selection_rows)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str, auth: AuthContext = Depends(get_auth_context)) -> SessionOut:
    session_row = _get_session_or_404(auth.client, session_id)
    selection_rows = sessions_repo.get_session_test_selections(auth.client, session_id)
    return session_out_from_rows(session_row, selection_rows)


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
    reading_row = readings_repo.insert_reading(
        auth.client,
        session_id=session_id,
        entered_by=auth.user_id,
        sequence_no=payload.sequence_no,
        direction=payload.direction.value,
        data=submission.reading.model_dump(mode="json"),
    )

    try:
        readings_repo.insert_result(
            auth.client,
            session_id=session_id,
            reading_id=reading_row["id"],
            result=submission.result_out.model_dump(mode="json"),
            passed=submission.result_out.passed,
        )
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
