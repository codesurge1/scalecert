from fastapi import APIRouter, Depends, HTTPException

from app.contracts.instrument import InstrumentIn, InstrumentOut, instrument_out_from_row
from app.contracts.session import SessionOut, session_out_from_rows
from app.deps import AuthContext, get_auth_context
from app.repositories import instruments as instruments_repo
from app.repositories import sessions as sessions_repo

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.post("", response_model=InstrumentOut, status_code=201)
def create_instrument(payload: InstrumentIn, auth: AuthContext = Depends(get_auth_context)) -> InstrumentOut:
    row = instruments_repo.insert_instrument(auth.client, auth.user_id, payload)
    return instrument_out_from_row(row)


@router.get("", response_model=list[InstrumentOut])
def list_instruments(auth: AuthContext = Depends(get_auth_context)) -> list[InstrumentOut]:
    rows = instruments_repo.list_instruments(auth.client)
    return [instrument_out_from_row(row) for row in rows]


@router.get("/{instrument_id}", response_model=InstrumentOut)
def get_instrument(instrument_id: str, auth: AuthContext = Depends(get_auth_context)) -> InstrumentOut:
    row = instruments_repo.get_instrument(auth.client, instrument_id)
    if row is None:
        # RLS returns zero rows for "doesn't exist" and "exists but not
        # visible to this caller" identically (CLAUDE.md: RLS fails
        # silently) — both surface as 404 here, deliberately not
        # distinguished, so a caller can't probe for other users' rows.
        raise HTTPException(status_code=404, detail="instrument not found")
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
    instrument_row = instruments_repo.get_instrument(auth.client, instrument_id)
    if instrument_row is None:
        raise HTTPException(status_code=404, detail="instrument not found")

    session_rows = sessions_repo.list_sessions_for_instrument(auth.client, instrument_id)
    return [
        session_out_from_rows(session_row, sessions_repo.get_session_test_selections(auth.client, session_row["id"]))
        for session_row in session_rows
    ]
