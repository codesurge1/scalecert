"""One specific, deliberately different Decimal-parsing policy from
`app.contracts.common.StrictDecimal`.

`StrictDecimal` governs untrusted CLIENT input and rejects a bare float
outright. This module governs the OPPOSITE boundary: parsing our OWN
Supabase/PostgREST response data, where `numeric` columns come back as JSON
numbers (Python `float` after json-decoding), not strings — rejecting them
would break every read. `Decimal(str(value))` is safe here because Python's
float repr is shortest-round-trip (verified empirically: `str(0.1) == "0.1"`,
not `"0.1000000000000000055511151231257827021181583404541015625"`), and this
data comes from Postgres's own `numeric` type via our own trusted query, not
from an arbitrary client payload.

Known follow-up, not solved here: for very large or very high-precision
values this could theoretically still lose a digit PostgREST's JSON-number
encoding never had space for in the first place; casting `numeric` to `text`
in the query (or a settings change) would close that gap. Not needed at the
magnitudes this project's instruments actually use.
"""

from decimal import Decimal
from typing import Any


def decimal_from_db_value(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (float, int, str)):
        return Decimal(str(value))
    raise TypeError(f"cannot parse {type(value).__name__} as Decimal from a DB row")
