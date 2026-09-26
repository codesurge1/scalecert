"""Pure instrument-registration business rules: no DB, no HTTP — just the
accuracy-class derivation and the "which class actually gets stored"
decision. Kept separate from routers/repositories specifically so it is
unit-testable without a live Supabase connection, the same reasoning as
services/weighing.py and services/sessions.py.
"""

from app.contracts.instrument import InstrumentIn
from engine.classification import classify_instrument
from engine.types import AccuracyClass


class InstrumentNotClassifiable(ValueError):
    """Raised when e/Max/Min (and d, if given) fit no OIML R76-1 Table 3
    accuracy class at all — carries the engine's own reason (which
    constraint failed, for which class(es) were even in range)."""


class AmbiguousAccuracyClass(ValueError):
    """Raised when e/Max/Min qualify for more than one accuracy class and
    the client either didn't submit `accuracy_class` or submitted one that
    isn't among the qualifying set — the client must pick among the classes
    that actually fit, never any other value."""

    def __init__(self, qualified_classes: tuple[AccuracyClass, ...]):
        self.qualified_classes = qualified_classes
        classes = ", ".join(c.value for c in qualified_classes)
        super().__init__(
            f"e/Max/Min qualify for more than one accuracy class ({classes}); "
            "submit accuracy_class as one of these."
        )


def derive_accuracy_class(payload: InstrumentIn) -> AccuracyClass:
    """The one place engine.classification.classify_instrument is called
    from the API layer, so registration can never disagree with itself
    about which class an instrument's own e/Max/Min actually support —
    accuracy_class is derived here, never trusted as a free client choice
    (CLAUDE.md-level rule for this feature, same shape as "the technician
    never enters L").

    Exactly one qualifying class -> that class, regardless of what (if
    anything) the client submitted in `accuracy_class` (it's ignored in
    this case — there's nothing to disambiguate). More than one -> the
    client's submitted `accuracy_class` must be one of the qualifying set,
    or this raises `AmbiguousAccuracyClass`. None -> raises
    `InstrumentNotClassifiable` with the engine's own reason. Both
    exceptions are ValueError subclasses; the router maps both to 422.
    """
    result = classify_instrument(
        e=payload.e_value,
        max_capacity=payload.max_capacity,
        min_capacity=payload.min_capacity,
        d=payload.d_value,
    )
    if not result.is_valid:
        raise InstrumentNotClassifiable(result.reason)

    if len(result.qualified_classes) == 1:
        return result.qualified_classes[0]

    if payload.accuracy_class is not None and payload.accuracy_class in result.qualified_classes:
        return payload.accuracy_class

    raise AmbiguousAccuracyClass(result.qualified_classes)
