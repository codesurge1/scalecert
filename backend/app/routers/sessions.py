import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

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
from app.contracts.instrument import instrument_params_from_row
from app.contracts.repeatability import RepeatabilityReadingSubmitIn, RepeatabilitySeriesOut
from app.contracts.sensitivity import (
    SensitivityCheckOut,
    SensitivityReadingRecordOut,
    SensitivityReadingSubmitIn,
    SensitivityResultOut,
    reading_and_result_to_record_out as sensitivity_reading_and_result_to_record_out,
)
from app.contracts.session import SessionIn, SessionOut, session_out_from_rows
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
from app.repositories import instruments as instruments_repo
from app.repositories import readings as readings_repo
from app.repositories import sessions as sessions_repo
from app.repositories.errors import RepositoryError
from app.services import discrimination as discrimination_service
from app.services import eccentricity as eccentricity_service
from app.services import repeatability as repeatability_service
from app.services import sensitivity as sensitivity_service
from app.services import tilting as tilting_service
from app.services import weighing as weighing_service
from app.services import zero_tare as zero_tare_service
from app.services.sessions import SessionNotDraft, ensure_session_is_draft
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
