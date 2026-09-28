"""Pure orchestration for the record-only clause-12.x disturbance tests: no
DB, no HTTP, no engine call — see app/contracts/disturbance.py for why no
computation is possible here. The only job is validating a submitted
`condition_key` against that test's own fixed condition list, read from the
OIML R 76-2 form for that clause (rendered as images via pdftoppm, the same
method used for every other form in this app — pages 24/25/29 for
12.1/12.2/12.4, and (feat/remaining-disturbance-forms) pages 27-28/32-33/34/
35-36 for 12.3/12.5/12.6/12.7 respectively) — all seven clause-12.x tests
are now built, completing the record-only category.

Each list reproduces its form's row structure faithfully, with one
documented simplification apiece (both noted inline and in
docs/architecture.md): 12.2(b) I/O circuits has 9 generic, blank
cable/interface slots on the real form (a technician fills in what's
connected, however many there are) — simplified to 3 fixed slots, since
"3 predefined slots" is what this app's fixed-condition-list model can
represent; a session that genuinely needs more than 3 I/O interfaces
tested records the rest in the free-text Remarks field. 12.6's own 10
blank cable/interface rows get the identical treatment, for the identical
reason.
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

# 12.3 Surges (R 76-2 pages 27-28) — part (a) AC mains power supply: three
# amplitude/connection groups (0.5 kV L->N, 1 kV L->PE, 1 kV N->PE), each
# with its own baseline then 3 positive + 3 negative surges synchronized at
# 0/90/180/270 degrees with the AC supply voltage (the form's own
# "amplitude/apply on x angle x polarity" structure). Part (b) any other
# kind of power supply: the same three connection groups, but a single
# fixed amplitude each (no angle synchronization — DC/other supplies have
# no AC waveform to synchronize with), baseline + positive + negative.
_SURGES_A_GROUPS = [
    ("0.5kv_ln", "0.5 kV, L→N"),
    ("1kv_lpe", "1 kV, L→PE"),
    ("1kv_npe", "1 kV, N→PE"),
]
_SURGES_ANGLES = ["0", "90", "180", "270"]
_SURGES_A = [
    row
    for group_key, group_label in _SURGES_A_GROUPS
    for row in (
        [
            {
                "condition_key": f"a_{group_key}_baseline",
                "label": f"(a) {group_label} — without disturbance",
                "group": "a",
                "has_fault_check": False,
            }
        ]
        + [
            {
                "condition_key": f"a_{group_key}_{angle}_{polarity}",
                "label": f"(a) {group_label}, {angle}°, {polarity_label}",
                "group": "a",
                "has_fault_check": True,
            }
            for angle in _SURGES_ANGLES
            for polarity, polarity_label in (("pos", "positive"), ("neg", "negative"))
        ]
    )
]
_SURGES_B_GROUPS = [
    ("ln", "L→N, 0.5 kV"),
    ("lpe", "L→PE, 1 kV"),
    ("npe", "N→PE, 1 kV"),
]
_SURGES_B = [
    row
    for group_key, group_label in _SURGES_B_GROUPS
    for row in (
        [
            {
                "condition_key": f"b_{group_key}_baseline",
                "label": f"(b) {group_label} — without disturbance",
                "group": "b",
                "has_fault_check": False,
            }
        ]
        + [
            {
                "condition_key": f"b_{group_key}_{polarity}",
                "label": f"(b) {group_label}, {polarity_label}",
                "group": "b",
                "has_fault_check": True,
            }
            for polarity, polarity_label in (("pos", "positive"), ("neg", "negative"))
        ]
    )
]
SURGES_CONDITIONS = _SURGES_A + _SURGES_B

# 12.5 Immunity to radiated electromagnetic fields (R 76-2 pages 32-33) —
# one baseline, then every combination of antenna polarization (vertical/
# horizontal) x facing the EUT (front/right/left/rear). The form's own
# "Antenna"/"Frequency range (MHz)" columns are free-text technician
# entries, not a further standardized condition axis, so they aren't
# modeled as separate rows here (the frequency-range choice itself is a
# session-level header field — B.3.6-applicable or not — not a per-row
# condition; see the frontend's headerExtras).
_RADIATED_EM_FACINGS = ["front", "right", "left", "rear"]
_RADIATED_EM_POLARIZATIONS = [("vertical", "Vertical"), ("horizontal", "Horizontal")]
RADIATED_EM_IMMUNITY_CONDITIONS = [
    {"condition_key": "baseline", "label": "Without disturbance", "has_fault_check": False},
] + [
    {
        "condition_key": f"{polarization}_{facing}",
        "label": f"{polarization_label} polarization, facing {facing.capitalize()}",
        "has_fault_check": True,
    }
    for polarization, polarization_label in _RADIATED_EM_POLARIZATIONS
    for facing in _RADIATED_EM_FACINGS
]

# 12.6 Immunity to conducted radio-frequency fields (R 76-2 page 34) — 10
# blank "Cable/Interface" row-pairs on the real form (a technician fills in
# whichever cable/interface is under test, however many there are);
# simplified to 3 fixed slots, the exact same convention and reasoning as
# 12.2(b)'s own I/O-circuits simplification, above. Each slot is a single
# 0.15-80 MHz sweep: baseline then one reading.
CONDUCTED_RF_IMMUNITY_CONDITIONS = [
    row
    for slot in (1, 2, 3)
    for row in (
        {
            "condition_key": f"slot_{slot}_baseline",
            "label": f"Cable/interface {slot} — without disturbance",
            "has_fault_check": False,
        },
        {
            "condition_key": f"slot_{slot}_sweep",
            "label": f"Cable/interface {slot}, 0.15–80 MHz sweep",
            "has_fault_check": True,
        },
    )
]

# 12.7 Electrical transients on instruments powered from a road vehicle
# power supply (R 76-2 pages 35-36) — part (a) conduction along supply
# lines of external 12 V/24 V batteries: each battery gets its own
# baseline then the 5 fixed test pulses (2a/2b/3a/3b/4) at that battery's
# own conducted voltage (the form's own footnote: pulse 2b only applies if
# the instrument isn't connected via the car's ignition switch — noted in
# the label itself, since this app's condition-list model has no separate
# "applicability footnote" field). Part (b) capacitive/inductive coupling
# via non-supply lines: the form itself already repeats 3 generic "other
# line" blocks per battery (not simplified from a larger number, unlike
# 12.2(b)/12.6 above — 3 is what the real form has), each with its own
# baseline then the 2 fixed pulses (a/b) at that battery's own voltage.
_RVT_A_PULSES = {
    "12v": [("2a", "+50 V"), ("2b", "+10 V"), ("3a", "−150 V"), ("3b", "+100 V"), ("4", "−7 V")],
    "24v": [("2a", "+50 V"), ("2b", "+20 V"), ("3a", "−200 V"), ("3b", "+200 V"), ("4", "−16 V")],
}
_RVT_BATTERIES = [("12v", "12 V battery"), ("24v", "24 V battery")]
_RVT_A = [
    row
    for battery, battery_label in _RVT_BATTERIES
    for row in (
        [
            {
                "condition_key": f"a_{battery}_baseline",
                "label": f"(a) {battery_label} — without disturbance",
                "group": "a",
                "has_fault_check": False,
            }
        ]
        + [
            {
                "condition_key": f"a_{battery}_{pulse}",
                "label": (
                    f"(a) {battery_label}, test pulse {pulse} ({voltage})"
                    + (" — only if not connected via the ignition switch" if pulse == "2b" else "")
                ),
                "group": "a",
                "has_fault_check": True,
            }
            for pulse, voltage in _RVT_A_PULSES[battery]
        ]
    )
]
_RVT_B_PULSES = {
    "12v": [("a", "−60 V"), ("b", "+40 V")],
    "24v": [("a", "−80 V"), ("b", "+80 V")],
}
_RVT_B = [
    row
    for battery, battery_label in _RVT_BATTERIES
    for slot in (1, 2, 3)
    for row in (
        [
            {
                "condition_key": f"b_{battery}_slot{slot}_baseline",
                "label": f"(b) {battery_label}, other line {slot} — without disturbance",
                "group": "b",
                "has_fault_check": False,
            }
        ]
        + [
            {
                "condition_key": f"b_{battery}_slot{slot}_{pulse}",
                "label": f"(b) {battery_label}, other line {slot}, pulse {pulse} ({voltage})",
                "group": "b",
                "has_fault_check": True,
            }
            for pulse, voltage in _RVT_B_PULSES[battery]
        ]
    )
]
ROAD_VEHICLE_TRANSIENTS_CONDITIONS = _RVT_A + _RVT_B

CONDITIONS_BY_TEST_TYPE = {
    "ac_mains_dips": AC_MAINS_DIPS_CONDITIONS,
    "electrical_bursts": ELECTRICAL_BURSTS_CONDITIONS,
    "electrostatic_discharges": ELECTROSTATIC_DISCHARGES_CONDITIONS,
    "surges": SURGES_CONDITIONS,
    "radiated_em_immunity": RADIATED_EM_IMMUNITY_CONDITIONS,
    "conducted_rf_immunity": CONDUCTED_RF_IMMUNITY_CONDITIONS,
    "road_vehicle_transients": ROAD_VEHICLE_TRANSIENTS_CONDITIONS,
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
