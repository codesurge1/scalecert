from fastapi import APIRouter, Depends, HTTPException

from app.contracts.instrument import InstrumentIn, InstrumentOut, instrument_out_from_row
from app.contracts.session import SessionOut, session_out_from_rows
from app.deps import AuthContext, get_auth_context
from app.repositories import instruments as instruments_repo
from app.repositories import sessions as sessions_repo
from app.repositories.errors import RepositoryError
from app.services.instruments import AmbiguousAccuracyClass, InstrumentNotClassifiable, derive_accuracy_class

router = APIRouter(prefix="/instruments", tags=["instruments"])


def _get_instrument_or_404(client, instrument_id: str) -> dict:
    # A RepositoryError (e.g. a malformed instrument_id hitting Postgres's
    # "invalid input syntax for type uuid") folds into the same 404 a
    # genuinely nonexistent/not-visible instrument gets — see the comment
    # below on the deliberate not-found/not-visible non-distinction.
    try:
        row = instruments_repo.get_instrument(client, instrument_id)
    except RepositoryError as exc:
        raise HTTPException(status_code=404, detail=f"instrument not found ({exc.hint})") from exc
    if row is None:
        # RLS returns zero rows for "doesn't exist" and "exists but not
        # visible to this caller" identically (CLAUDE.md: RLS fails
        # silently) — both surface as 404 here, deliberately not
        # distinguished, so a caller can't probe for other users' rows.
        raise HTTPException(status_code=404, detail="instrument not found")
    return row


@router.post("", response_model=InstrumentOut, status_code=201)
def create_instrument(payload: InstrumentIn, auth: AuthContext = Depends(get_auth_context)) -> InstrumentOut:
    # accuracy_class is never trusted from the client — derived here from
    # e/Max/Min (and d, if given) via OIML R76-1 Table 3
    # (engine.classification.classify_instrument). An instrument whose
    # values fit no class at all, or ambiguously fit several without the
    # client picking among them, is rejected before anything is written.
    try:
        derived_class = derive_accuracy_class(payload)
    except (InstrumentNotClassifiable, AmbiguousAccuracyClass) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        row = instruments_repo.insert_instrument(auth.client, auth.user_id, payload, derived_class)
    except RepositoryError as exc:
        raise HTTPException(
            status_code=403 if exc.likely_rls else 500,
            detail=f"could not register the instrument ({exc.operation} on {exc.table}): {exc.hint}",
        ) from exc
    return instrument_out_from_row(row)


@router.get("", response_model=list[InstrumentOut])
def list_instruments(auth: AuthContext = Depends(get_auth_context)) -> list[InstrumentOut]:
    rows = instruments_repo.list_instruments(auth.client)
    return [instrument_out_from_row(row) for row in rows]


@router.get("/{instrument_id}", response_model=InstrumentOut)
def get_instrument(instrument_id: str, auth: AuthContext = Depends(get_auth_context)) -> InstrumentOut:
    row = _get_instrument_or_404(auth.client, instrument_id)
    return instrument_out_from_row(row)


@router.get("/{instrument_id}/sessions", response_model=list[SessionOut])
def list_instrument_sessions(
    instrument_id: str, auth: AuthContext = Depends(get_auth_context)
) -> list[SessionOut]:
    """The instrument-detail page's session list — every verification
    session opened against this instrument, newest first, each with its
    test_selections (same shape `GET /sessions/{id}` already returns, reused
    rather than a slimmer duplicate contract). RLS-scoped like every other
    route.
    """
    _get_instrument_or_404(auth.client, instrument_id)

    session_rows = sessions_repo.list_sessions_for_instrument(auth.client, instrument_id)
    return [
        session_out_from_rows(session_row, sessions_repo.get_session_test_selections(auth.client, session_row["id"]))
        for session_row in session_rows
    ]
