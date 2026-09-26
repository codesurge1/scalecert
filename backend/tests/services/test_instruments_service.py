"""Pure unit tests for app.services.instruments — no DB, no HTTP."""

from decimal import Decimal

import pytest

from app.contracts.instrument import InstrumentIn
from app.services.instruments import (
    AmbiguousAccuracyClass,
    InstrumentNotClassifiable,
    derive_accuracy_class,
)
from engine.types import AccuracyClass

D = Decimal


def _instrument_in(**overrides):
    base = dict(e_value="1", max_capacity="6000", min_capacity="20", indication_type="digital")
    base.update(overrides)
    return InstrumentIn(**base)


def test_derives_the_sole_qualifying_class_ignoring_any_client_hint():
    # n=6000 uniquely fits Class III (see test_instruments_router.py's
    # _VALID_BODY comment for the full reasoning) — a client-submitted
    # accuracy_class is irrelevant when only one class qualifies at all.
    payload = _instrument_in(accuracy_class="IIII")
    assert derive_accuracy_class(payload) is AccuracyClass.III


def test_derives_without_any_client_accuracy_class_at_all():
    payload = _instrument_in()
    assert payload.accuracy_class is None
    assert derive_accuracy_class(payload) is AccuracyClass.III


def test_raises_instrument_not_classifiable_when_nothing_fits():
    payload = _instrument_in(max_capacity="20", min_capacity="1")
    with pytest.raises(InstrumentNotClassifiable) as excinfo:
        derive_accuracy_class(payload)
    assert "No accuracy class fits" in str(excinfo.value)


def test_raises_ambiguous_when_multiple_qualify_and_no_hint_given():
    # e=1g, Max=8000g, Min=50g qualifies for both II and III.
    payload = _instrument_in(max_capacity="8000", min_capacity="50")
    with pytest.raises(AmbiguousAccuracyClass) as excinfo:
        derive_accuracy_class(payload)
    assert set(excinfo.value.qualified_classes) == {AccuracyClass.II, AccuracyClass.III}


def test_accepts_a_valid_hint_when_multiple_qualify():
    payload = _instrument_in(max_capacity="8000", min_capacity="50", accuracy_class="II")
    assert derive_accuracy_class(payload) is AccuracyClass.II


def test_raises_ambiguous_when_hint_is_not_among_the_qualifying_classes():
    payload = _instrument_in(max_capacity="8000", min_capacity="50", accuracy_class="IIII")
    with pytest.raises(AmbiguousAccuracyClass):
        derive_accuracy_class(payload)


def test_raises_instrument_not_classifiable_for_invalid_e_format():
    payload = _instrument_in(e_value="3", max_capacity="3000", min_capacity="60")
    with pytest.raises(InstrumentNotClassifiable) as excinfo:
        derive_accuracy_class(payload)
    assert "verification scale interval" in str(excinfo.value)
