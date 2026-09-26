"""No silent defaults (CLAUDE.md / Step 3): a missing or wrong-typed required
input raises an explicit error — it is never guessed.
"""

from decimal import Decimal

import pytest

from engine.mpe import lookup_mpe
from engine.types import AccuracyClass, VerificationType
from engine.weighing import compute_weighing_result

D = Decimal

_VALID_KWARGS = dict(
    accuracy_class=AccuracyClass.III,
    verification_type=VerificationType.INITIAL,
    e=D("1"),
    L=D("300"),
    I=D("300.4"),
    delta_l=D("0.5"),
    E0=D("0"),
)


@pytest.mark.parametrize("missing", ["accuracy_class", "verification_type", "e", "L", "I", "delta_l", "E0"])
def test_compute_weighing_result_requires_every_argument(missing):
    kwargs = {k: v for k, v in _VALID_KWARGS.items() if k != missing}
    with pytest.raises(TypeError):
        compute_weighing_result(**kwargs)


@pytest.mark.parametrize("bad_field", ["e", "L", "I", "delta_l", "E0"])
def test_compute_weighing_result_rejects_float_instead_of_decimal(bad_field):
    kwargs = dict(_VALID_KWARGS)
    kwargs[bad_field] = float(kwargs[bad_field])  # a plausible mistake: float, not Decimal
    with pytest.raises(TypeError):
        compute_weighing_result(**kwargs)


def test_compute_weighing_result_rejects_wrong_type_enum_fields():
    kwargs = dict(_VALID_KWARGS)
    kwargs["accuracy_class"] = "III"  # a bare string, not the AccuracyClass enum
    with pytest.raises(TypeError):
        compute_weighing_result(**kwargs)


def test_lookup_mpe_rejects_float_m():
    with pytest.raises(TypeError):
        lookup_mpe(
            accuracy_class=AccuracyClass.III,
            m=300.0,
            e=D("1"),
            verification_type=VerificationType.INITIAL,
        )


def test_lookup_mpe_rejects_negative_m():
    with pytest.raises(ValueError):
        lookup_mpe(
            accuracy_class=AccuracyClass.III,
            m=D("-1"),
            e=D("1"),
            verification_type=VerificationType.INITIAL,
        )


def test_compute_weighing_result_rejects_negative_load():
    kwargs = dict(_VALID_KWARGS)
    kwargs["L"] = D("-1")
    with pytest.raises(ValueError):
        compute_weighing_result(**kwargs)
