"""Pure unit tests for app.services.disturbance — no DB, no HTTP, no engine
(there is nothing to compute; see the module's own docstring)."""

import pytest

from app.services.disturbance import (
    AC_MAINS_DIPS_CONDITIONS,
    CONDUCTED_RF_IMMUNITY_CONDITIONS,
    ELECTRICAL_BURSTS_CONDITIONS,
    ELECTROSTATIC_DISCHARGES_CONDITIONS,
    RADIATED_EM_IMMUNITY_CONDITIONS,
    ROAD_VEHICLE_TRANSIENTS_CONDITIONS,
    SURGES_CONDITIONS,
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
    assert conditions_for("surges") == SURGES_CONDITIONS
    assert conditions_for("radiated_em_immunity") == RADIATED_EM_IMMUNITY_CONDITIONS
    assert conditions_for("conducted_rf_immunity") == CONDUCTED_RF_IMMUNITY_CONDITIONS
    assert conditions_for("road_vehicle_transients") == ROAD_VEHICLE_TRANSIENTS_CONDITIONS


def test_conditions_for_unknown_test_type_raises():
    with pytest.raises(UnknownTestType):
        conditions_for("tare")  # a real OIML clause, never built (Tare, CLAUDE.md scope)


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


# -- 12.3 Surges -------------------------------------------------------------


def test_surges_has_36_rows_part_a_and_part_b():
    conditions = conditions_for("surges")
    part_a = [c for c in conditions if c["group"] == "a"]
    part_b = [c for c in conditions if c["group"] == "b"]
    assert len(part_a) == 27  # 3 groups x (1 baseline + 4 angles x 2 polarities)
    assert len(part_b) == 9  # 3 groups x (1 baseline + pos + neg)
    assert len(conditions) == 36


def test_surges_baselines_have_no_fault_check():
    conditions = conditions_for("surges")
    baselines = [c for c in conditions if c["condition_key"].endswith("_baseline")]
    assert len(baselines) == 6  # 3 groups x 2 parts
    assert all(not c["has_fault_check"] for c in baselines)


# -- 12.5 Immunity to radiated electromagnetic fields ------------------------


def test_radiated_em_immunity_has_baseline_plus_polarization_x_facing():
    conditions = conditions_for("radiated_em_immunity")
    assert len(conditions) == 9  # 1 baseline + 2 polarizations x 4 facings
    assert conditions[0]["condition_key"] == "baseline"
    assert conditions[0]["has_fault_check"] is False
    assert all(c["has_fault_check"] for c in conditions[1:])
    assert {c["condition_key"] for c in conditions[1:]} == {
        f"{pol}_{facing}" for pol in ("vertical", "horizontal") for facing in ("front", "right", "left", "rear")
    }


# -- 12.6 Immunity to conducted radio-frequency fields -----------------------


def test_conducted_rf_immunity_has_3_slots_baseline_plus_sweep():
    conditions = conditions_for("conducted_rf_immunity")
    assert len(conditions) == 6  # 3 slots x (baseline + sweep)
    baselines = [c for c in conditions if not c["has_fault_check"]]
    assert len(baselines) == 3


# -- 12.7 Road vehicle transients ---------------------------------------------


def test_road_vehicle_transients_has_30_rows_part_a_and_part_b():
    conditions = conditions_for("road_vehicle_transients")
    part_a = [c for c in conditions if c["group"] == "a"]
    part_b = [c for c in conditions if c["group"] == "b"]
    assert len(part_a) == 12  # 2 batteries x (1 baseline + 5 pulses)
    assert len(part_b) == 18  # 2 batteries x 3 slots x (1 baseline + 2 pulses)
    assert len(conditions) == 30


def test_road_vehicle_transients_pulse_2b_notes_ignition_switch_caveat():
    condition = condition_by_key("road_vehicle_transients", "a_12v_2b")
    assert "ignition switch" in condition["label"]
    condition_3a = condition_by_key("road_vehicle_transients", "a_12v_3a")
    assert "ignition switch" not in condition_3a["label"]


def test_road_vehicle_transients_voltages_differ_by_battery():
    pulse_2a_12v = condition_by_key("road_vehicle_transients", "a_12v_2a")
    pulse_2a_24v = condition_by_key("road_vehicle_transients", "a_24v_2a")
    assert "+50 V" in pulse_2a_12v["label"]
    assert "+50 V" in pulse_2a_24v["label"]
    pulse_3a_12v = condition_by_key("road_vehicle_transients", "a_12v_3a")
    pulse_3a_24v = condition_by_key("road_vehicle_transients", "a_24v_3a")
    assert "−150 V" in pulse_3a_12v["label"]
    assert "−200 V" in pulse_3a_24v["label"]


def test_road_vehicle_transients_all_condition_keys_unique():
    conditions = conditions_for("road_vehicle_transients")
    keys = [c["condition_key"] for c in conditions]
    assert len(keys) == len(set(keys))
