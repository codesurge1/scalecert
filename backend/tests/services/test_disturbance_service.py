"""Pure unit tests for app.services.disturbance — no DB, no HTTP, no engine
(there is nothing to compute; see the module's own docstring)."""

import pytest

from app.services.disturbance import (
    AC_MAINS_DIPS_CONDITIONS,
    ELECTRICAL_BURSTS_CONDITIONS,
    ELECTROSTATIC_DISCHARGES_CONDITIONS,
    UnknownConditionKey,
    UnknownTestType,
    condition_by_key,
    condition_index,
    conditions_for,
)


def test_conditions_for_known_test_types():
    assert conditions_for("ac_mains_dips") == AC_MAINS_DIPS_CONDITIONS
    assert conditions_for("electrical_bursts") == ELECTRICAL_BURSTS_CONDITIONS
    assert conditions_for("electrostatic_discharges") == ELECTROSTATIC_DISCHARGES_CONDITIONS


def test_conditions_for_unknown_test_type_raises():
    with pytest.raises(UnknownTestType):
        conditions_for("surges")  # deferred, not built this task


def test_ac_mains_dips_has_baseline_plus_six_fixed_conditions():
    conditions = conditions_for("ac_mains_dips")
    assert len(conditions) == 7
    assert conditions[0]["condition_key"] == "baseline"
    assert conditions[0]["has_fault_check"] is False
    assert all(c["has_fault_check"] for c in conditions[1:])


def test_electrical_bursts_has_9_rows_part_a_and_9_rows_part_b():
    conditions = conditions_for("electrical_bursts")
    part_a = [c for c in conditions if c["group"] == "a"]
    part_b = [c for c in conditions if c["group"] == "b"]
    assert len(part_a) == 9  # 3 baselines + 3 connections x pos/neg
    assert len(part_b) == 9  # 3 slots x (baseline + pos + neg)


def test_electrostatic_discharges_has_10_rows_part_a_and_16_rows_part_b():
    conditions = conditions_for("electrostatic_discharges")
    part_a = [c for c in conditions if c["group"] == "a"]
    part_b = [c for c in conditions if c["group"] == "b"]
    assert len(part_a) == 10  # 2 baselines + 4 levels x pos/neg
    assert len(part_b) == 16  # 2 planes x (2 baselines + 3 levels x pos/neg)


def test_condition_index_matches_position():
    assert condition_index("ac_mains_dips", "baseline") == 0
    assert condition_index("ac_mains_dips", "interrupt_0pct_250cycles") == 6


def test_condition_index_raises_for_unknown_key():
    with pytest.raises(UnknownConditionKey):
        condition_index("ac_mains_dips", "not-a-real-condition")


def test_condition_by_key_returns_the_full_condition():
    condition = condition_by_key("ac_mains_dips", "dip_40pct_10cycles")
    assert condition["label"] == "40 % for 10 cycles"
    assert condition["has_fault_check"] is True
