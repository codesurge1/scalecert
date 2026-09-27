"""Pure orchestration for the record-only clause-12.x disturbance tests: no
DB, no HTTP, no engine call — see app/contracts/disturbance.py for why no
computation is possible here. The only job is validating a submitted
`condition_key` against that test's own fixed condition list, read from the
OIML R 76-2 form for that clause (rendered as images via pdftoppm, the same
method used for every other form in this app — pages 24/25/29 for
12.1/12.2/12.4 respectively).

Each list reproduces its form's row structure faithfully, with one
documented simplification apiece (both noted inline and in
docs/architecture.md): 12.2(b) I/O circuits has 9 generic, blank
cable/interface slots on the real form (a technician fills in what's
connected, however many there are) — simplified to 3 fixed slots, since
"3 predefined slots" is what this app's fixed-condition-list model can
represent; a session that genuinely needs more than 3 I/O interfaces
tested records the rest in the free-text Remarks field.
"""

# 12.1 AC mains voltage dips and short interruptions (R 76-2 page 24) — one
# baseline reading, then the six fixed amplitude/duration conditions the
# standard specifies (never technician-chosen).
AC_MAINS_DIPS_CONDITIONS = [
    {"condition_key": "baseline", "label": "Without disturbance", "has_fault_check": False},
    {"condition_key": "dip_0pct_0.5cycle", "label": "0 % for 0.5 cycle", "has_fault_check": True},
    {"condition_key": "dip_0pct_1cycle", "label": "0 % for 1 cycle", "has_fault_check": True},
    {"condition_key": "dip_40pct_10cycles", "label": "40 % for 10 cycles", "has_fault_check": True},
    {"condition_key": "dip_70pct_25cycles", "label": "70 % for 25 cycles", "has_fault_check": True},
    {"condition_key": "dip_80pct_250cycles", "label": "80 % for 250 cycles", "has_fault_check": True},
    {"condition_key": "interrupt_0pct_250cycles", "label": "0 % for 250 cycles (short interruption)", "has_fault_check": True},
]

# 12.2 Electrical bursts (R 76-2 pages 25-26) — part (a) mains power supply
# lines (L/N/PE x positive/negative, each preceded by its own baseline);
# part (b) I/O circuits and communication lines, simplified to 3 generic
# cable/interface slots (see module docstring) instead of the form's 9
# blank ones.
_BURSTS_A = [
    {"condition_key": "a_baseline_l", "label": "(a) Without disturbance — before L -> ground", "group": "a", "has_fault_check": False},
    {"condition_key": "a_l_pos", "label": "(a) L -> ground, positive", "group": "a", "has_fault_check": True},
    {"condition_key": "a_l_neg", "label": "(a) L -> ground, negative", "group": "a", "has_fault_check": True},
    {"condition_key": "a_baseline_n", "label": "(a) Without disturbance — before N -> ground", "group": "a", "has_fault_check": False},
    {"condition_key": "a_n_pos", "label": "(a) N -> ground, positive", "group": "a", "has_fault_check": True},
    {"condition_key": "a_n_neg", "label": "(a) N -> ground, negative", "group": "a", "has_fault_check": True},
    {"condition_key": "a_baseline_pe", "label": "(a) Without disturbance — before PE -> ground", "group": "a", "has_fault_check": False},
    {"condition_key": "a_pe_pos", "label": "(a) PE -> ground, positive", "group": "a", "has_fault_check": True},
    {"condition_key": "a_pe_neg", "label": "(a) PE -> ground, negative", "group": "a", "has_fault_check": True},
]
_BURSTS_B = [
    row
    for slot in (1, 2, 3)
    for row in (
        {
            "condition_key": f"b_baseline_{slot}",
            "label": f"(b) Without disturbance — cable/interface {slot}",
            "group": "b",
            "has_fault_check": False,
        },
        {"condition_key": f"b_{slot}_pos", "label": f"(b) Cable/interface {slot}, positive", "group": "b", "has_fault_check": True},
        {"condition_key": f"b_{slot}_neg", "label": f"(b) Cable/interface {slot}, negative", "group": "b", "has_fault_check": True},
    )
]
ELECTRICAL_BURSTS_CONDITIONS = _BURSTS_A + _BURSTS_B

# 12.4 Electrostatic discharges (R 76-2 pages 29-30) — part (a) direct
# application (2/4/6/8 kV x positive/negative, 8 kV is air discharges per
# the form's own note); part (b) indirect application, horizontal AND
# vertical coupling planes (2/4/6 kV x positive/negative each — no 8 kV
# tier for indirect, matching the form exactly).
_ESD_A = [
    {"condition_key": "a_baseline_pos", "label": "(a) Direct — without disturbance (before positive)", "group": "a", "has_fault_check": False},
    {"condition_key": "a_2kv_pos", "label": "(a) Direct, 2 kV, positive", "group": "a", "has_fault_check": True},
    {"condition_key": "a_4kv_pos", "label": "(a) Direct, 4 kV, positive", "group": "a", "has_fault_check": True},
    {"condition_key": "a_6kv_pos", "label": "(a) Direct, 6 kV, positive", "group": "a", "has_fault_check": True},
    {"condition_key": "a_8kv_pos", "label": "(a) Direct, 8 kV (air discharges), positive", "group": "a", "has_fault_check": True},
    {"condition_key": "a_baseline_neg", "label": "(a) Direct — without disturbance (before negative)", "group": "a", "has_fault_check": False},
    {"condition_key": "a_2kv_neg", "label": "(a) Direct, 2 kV, negative", "group": "a", "has_fault_check": True},
    {"condition_key": "a_4kv_neg", "label": "(a) Direct, 4 kV, negative", "group": "a", "has_fault_check": True},
    {"condition_key": "a_6kv_neg", "label": "(a) Direct, 6 kV, negative", "group": "a", "has_fault_check": True},
    {"condition_key": "a_8kv_neg", "label": "(a) Direct, 8 kV (air discharges), negative", "group": "a", "has_fault_check": True},
]
_ESD_B = [
    row
    for plane, plane_label in (("h", "Horizontal"), ("v", "Vertical"))
    for row in (
        {
            "condition_key": f"b_{plane}_baseline_pos",
            "label": f"(b) {plane_label} plane — without disturbance (before positive)",
            "group": "b",
            "has_fault_check": False,
        },
        {"condition_key": f"b_{plane}_2kv_pos", "label": f"(b) {plane_label} plane, 2 kV, positive", "group": "b", "has_fault_check": True},
        {"condition_key": f"b_{plane}_4kv_pos", "label": f"(b) {plane_label} plane, 4 kV, positive", "group": "b", "has_fault_check": True},
        {"condition_key": f"b_{plane}_6kv_pos", "label": f"(b) {plane_label} plane, 6 kV, positive", "group": "b", "has_fault_check": True},
        {
            "condition_key": f"b_{plane}_baseline_neg",
            "label": f"(b) {plane_label} plane — without disturbance (before negative)",
            "group": "b",
            "has_fault_check": False,
        },
        {"condition_key": f"b_{plane}_2kv_neg", "label": f"(b) {plane_label} plane, 2 kV, negative", "group": "b", "has_fault_check": True},
        {"condition_key": f"b_{plane}_4kv_neg", "label": f"(b) {plane_label} plane, 4 kV, negative", "group": "b", "has_fault_check": True},
        {"condition_key": f"b_{plane}_6kv_neg", "label": f"(b) {plane_label} plane, 6 kV, negative", "group": "b", "has_fault_check": True},
    )
]
ELECTROSTATIC_DISCHARGES_CONDITIONS = _ESD_A + _ESD_B

CONDITIONS_BY_TEST_TYPE = {
    "ac_mains_dips": AC_MAINS_DIPS_CONDITIONS,
    "electrical_bursts": ELECTRICAL_BURSTS_CONDITIONS,
    "electrostatic_discharges": ELECTROSTATIC_DISCHARGES_CONDITIONS,
}


class UnknownTestType(ValueError):
    """Raised for a test_type this module doesn't know a condition list
    for — a programming error (router registers only known types), never a
    client-reachable input."""


class UnknownConditionKey(ValueError):
    """Raised when a submitted condition_key isn't in that test's own
    fixed list."""


def conditions_for(test_type: str) -> list[dict]:
    try:
        return CONDITIONS_BY_TEST_TYPE[test_type]
    except KeyError as exc:
        raise UnknownTestType(f"{test_type!r} has no disturbance condition list") from exc


def condition_index(test_type: str, condition_key: str) -> int:
    conditions = conditions_for(test_type)
    for index, condition in enumerate(conditions):
        if condition["condition_key"] == condition_key:
            return index
    raise UnknownConditionKey(f"{condition_key!r} is not one of this test's conditions ({test_type})")


def condition_by_key(test_type: str, condition_key: str) -> dict:
    return conditions_for(test_type)[condition_index(test_type, condition_key)]
