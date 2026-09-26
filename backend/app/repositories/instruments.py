from supabase import Client

from app.contracts.instrument import InstrumentIn, instrument_insert_payload
from app.repositories.errors import run_insert, run_select

TABLE = "instruments"


def insert_instrument(client: Client, registered_by: str, payload: InstrumentIn) -> dict:
    data = instrument_insert_payload(registered_by, payload)
    return run_insert(
        client.table(TABLE).insert(data),
        table=TABLE,
        hint="registering an instrument — check policy 'instruments_insert_own' (registered_by must equal the caller)",
    )


def list_instruments(client: Client) -> list[dict]:
    return run_select(client.table(TABLE).select("*"), table=TABLE, hint="listing instruments")


def get_instrument(client: Client, instrument_id: str) -> dict | None:
    rows = run_select(
        client.table(TABLE).select("*").eq("id", instrument_id),
        table=TABLE,
        hint=f"fetching instrument {instrument_id!r} — id may be malformed, or check policy 'instruments_select_auth'",
    )
    return rows[0] if rows else None
