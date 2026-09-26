from fastapi import APIRouter, Depends, HTTPException

from app.contracts.instrument import InstrumentIn, InstrumentOut, instrument_out_from_row
from app.deps import AuthContext, get_auth_context
from app.repositories import instruments as instruments_repo

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
