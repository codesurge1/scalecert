from supabase import Client

from app.contracts.instrument import InstrumentIn, instrument_insert_payload

TABLE = "instruments"


def insert_instrument(client: Client, registered_by: str, payload: InstrumentIn) -> dict:
    data = instrument_insert_payload(registered_by, payload)
    rows = client.table(TABLE).insert(data).execute().data
    return rows[0]


def list_instruments(client: Client) -> list[dict]:
    return client.table(TABLE).select("*").execute().data


def get_instrument(client: Client, instrument_id: str) -> dict | None:
    rows = client.table(TABLE).select("*").eq("id", instrument_id).execute().data
    return rows[0] if rows else None
