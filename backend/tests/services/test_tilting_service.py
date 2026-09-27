"""Pure unit tests for app.services.tilting — no DB, no HTTP."""

from decimal import Decimal

from app.contracts.common import IndicationType
from app.contracts.instrument import InstrumentParams
from app.services.tilting import build_mid_load, compute_state
from engine.types import AccuracyClass, VerificationType

D = Decimal

# Max=1000g, e=1g, Class III -> mid load 500 (m=500, Band 1, mpe=0.5g),
# Max load 1000 (m=1000, Band 2, mpe=1.0g) — the two loaded rows genuinely
# differ in mpe, same reasoning as the engine-level tests.
_INSTRUMENT = InstrumentParams(
    accuracy_class=AccuracyClass.III, e_value=D("1"), max_capacity=D("1000"), min_capacity=D("10"),
    indication_type=IndicationType.DIGITAL, is_mobile=True, d_value=None,
)


def test_build_mid_load_is_half_of_max():
    assert build_mid_load(_INSTRUMENT) == D("500")


def test_compute_state_with_no_readings_still_knows_l_and_mpe():
    state = compute_state(_INSTRUMENT, VerificationType.INITIAL, [])
    assert state.L == D("500")
    assert state.max_capacity == D("1000")
    assert state.mpe_l == D("0.5")
    assert state.mpe_max == D("1.0")
    assert state.readings == []
    assert state.passed is None
    assert state.unloaded_within_limit is None


def test_compute_state_computes_unloaded_check_with_just_reference_and_one_tilted():
    readings = [("unloaded", 1, D("100.5"), D("0.5")), ("unloaded", 2, D("100.6"), D("0.5"))]
    state = compute_state(_INSTRUMENT, VerificationType.INITIAL, readings)
    assert len(state.readings) == 2
    assert state.readings[0].E == D("100.5")
    assert state.unloaded_max_abs_deviation == D("0.1")
    assert state.unloaded_within_limit is True
    # Loaded checks can't run yet — no loaded readings submitted.
    assert state.loaded_l_within_mpe is None
    assert state.passed is None


def test_compute_state_loaded_reading_is_skipped_without_its_own_unloaded_e0():
    # Position 3's loaded_l reading exists, but position 3 has no unloaded
    # reading yet — it must not appear in the computed readings/checks.
    readings = [("unloaded", 1, D("100.0"), D("0.5")), ("loaded_l", 3, D("600.0"), D("0.5"))]
    state = compute_state(_INSTRUMENT, VerificationType.INITIAL, readings)
    phases_positions = [(r.phase, r.position_no) for r in state.readings]
    assert ("loaded_l", 3) not in phases_positions


def test_compute_state_full_dataset_passes():
    readings = [
        ("unloaded", 1, D("100.5"), D("0.5")),  # E0 = 100.5
        ("unloaded", 2, D("100.6"), D("0.5")),  # E0 = 100.6
        ("loaded_l", 1, D("600.7"), D("0.5")),  # E=600.7-500=100.7 -> Ec=100.7-100.5=0.2
        ("loaded_l", 2, D("600.9"), D("0.5")),  # E=100.9 -> Ec=100.9-100.6=0.3
        ("loaded_max", 1, D("1101.0"), D("0.5")),  # E=1101-1000=101.0 -> Ec=101.0-100.5=0.5
        ("loaded_max", 2, D("1101.0"), D("0.5")),  # E=101.0 -> Ec=101.0-100.6=0.4
    ]
    state = compute_state(_INSTRUMENT, VerificationType.INITIAL, readings)

    assert state.unloaded_max_abs_deviation == D("0.1")
    assert state.unloaded_within_limit is True

    assert state.loaded_l_max_abs_deviation == D("0.1")  # |0.2 - 0.3|
    assert state.loaded_l_within_mpe is True  # 0.1 <= mpe_l (0.5)

    assert state.loaded_max_max_abs_deviation == D("0.1")  # |0.5 - 0.4|
    assert state.loaded_max_within_mpe is True  # 0.1 <= mpe_max (1.0)

    assert state.passed is True
    assert len(state.readings) == 6


def test_compute_state_fails_when_loaded_max_criterion_fails():
    readings = [
        ("unloaded", 1, D("100.0"), D("0.5")),
        ("unloaded", 2, D("100.0"), D("0.5")),
        ("loaded_l", 1, D("600.0"), D("0.5")),  # Ec1 = 100.0 - 100.0 = 0
        ("loaded_l", 2, D("600.0"), D("0.5")),  # Ec2 = 0
        ("loaded_max", 1, D("1100.0"), D("0.5")),  # Ec1 = 100.0 - 100.0 = 0
        ("loaded_max", 2, D("1102.0"), D("0.5")),  # Ec2 = 2.0 -> dev 2.0 > mpe_max (1.0)
    ]
    state = compute_state(_INSTRUMENT, VerificationType.INITIAL, readings)
    assert state.loaded_max_within_mpe is False
    assert state.passed is False


def test_compute_state_orders_readings_by_phase_then_position():
    readings = [
        ("loaded_max", 2, D("1100.0"), D("0.5")),
        ("unloaded", 2, D("100.0"), D("0.5")),
        ("unloaded", 1, D("100.0"), D("0.5")),
        ("loaded_l", 1, D("600.0"), D("0.5")),
    ]
    state = compute_state(_INSTRUMENT, VerificationType.INITIAL, readings)
    ordered = [(r.phase, r.position_no) for r in state.readings]
    assert ordered == [("unloaded", 1), ("unloaded", 2), ("loaded_l", 1), ("loaded_max", 2)]
