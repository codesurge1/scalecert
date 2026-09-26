"""The canonical worked example (docs/plan.md, Phase 1): Class III, e=1g, initial
verification, load 300g. This is written and run to fail BEFORE engine/mpe.py and
engine/weighing.py exist — it's the spec, not a confirmation.

delta_l is set to e/2 so the engine's "+ 1/2*e - delta_l" term cancels to zero,
leaving E = I - L: the simplest input choice that reproduces the task's stated
worked-example error values (I=300.4 -> E=+0.4, I=300.6 -> E=+0.6) exactly.
"""

from decimal import Decimal

from engine.types import AccuracyClass, VerificationType
from engine.weighing import compute_weighing_result


def test_worked_example_pass():
    # 300g at e=1g -> m=300 -> Band 1 (0 <= m <= 500) -> mpe = 0.5e = 0.5g.
    e = Decimal("1")
    L = Decimal("300")
    delta_l = e / 2
    E0 = Decimal("0")

    result = compute_weighing_result(
        accuracy_class=AccuracyClass.III,
        verification_type=VerificationType.INITIAL,
        e=e,
        L=L,
        I=Decimal("300.4"),
        delta_l=delta_l,
        E0=E0,
    )

    assert result.mpe == Decimal("0.5")
    assert result.E == Decimal("0.4")
    assert result.Ec == Decimal("0.4")
    assert result.passed is True


def test_worked_example_fail():
    e = Decimal("1")
    L = Decimal("300")
    delta_l = e / 2
    E0 = Decimal("0")

    result = compute_weighing_result(
        accuracy_class=AccuracyClass.III,
        verification_type=VerificationType.INITIAL,
        e=e,
        L=L,
        I=Decimal("300.6"),
        delta_l=delta_l,
        E0=E0,
    )

    assert result.mpe == Decimal("0.5")
    assert result.E == Decimal("0.6")
    assert result.Ec == Decimal("0.6")
    assert result.passed is False
