"""Pure Tilting-test orchestration: no DB, no HTTP. Like Repeatability, the
pass criteria are whole-set properties (not any single reading), so there is
one function, `compute_state`, that both the readings-POST route (recompute
after inserting a new reading) and the readings-GET route (recompute on
load) call identically — a single source of truth for "what does the test
look like right now."
"""

from decimal import Decimal
from typing import Dict, Sequence, Tuple

from app.contracts.instrument import InstrumentParams
from app.contracts.tilting import TiltingReadingRecordOut, TiltingStateOut
from engine.mpe import lookup_mpe
from engine.tilting import (
    REFERENCE_POSITION,
    compute_tilt_loaded_reading,
    compute_tilt_unloaded_reading,
    compute_tilting_loaded_check,
    compute_tilting_unloaded_check,
    generate_tilting_mid_load,
)
from engine.types import VerificationType

# A stored reading, as fetched from the DB: (phase, position_no, I, delta_l).
StoredReading = Tuple[str, int, Decimal, Decimal]

_PHASE_ORDER = ("unloaded", "loaded_l", "loaded_max")


def build_mid_load(instrument: InstrumentParams) -> Decimal:
    return generate_tilting_mid_load(max_capacity=instrument.max_capacity)


def compute_state(
    instrument: InstrumentParams,
    verification_type: VerificationType,
    stored_readings: Sequence[StoredReading],
) -> TiltingStateOut:
    L = build_mid_load(instrument)
    max_capacity = instrument.max_capacity
    e = instrument.e_value
    accuracy_class = instrument.accuracy_class

    # mpe for both loaded rows is always knowable, even with zero readings.
    mpe_l = lookup_mpe(accuracy_class=accuracy_class, m=L / e, e=e, verification_type=verification_type).mpe_grams
    mpe_max = lookup_mpe(
        accuracy_class=accuracy_class, m=max_capacity / e, e=e, verification_type=verification_type
    ).mpe_grams

    by_phase: Dict[str, Dict[int, Tuple[Decimal, Decimal]]] = {phase: {} for phase in _PHASE_ORDER}
    for phase, position_no, I, delta_l in stored_readings:
        by_phase[phase][position_no] = (I, delta_l)

    record_rows: list[TiltingReadingRecordOut] = []

    # Unloaded readings establish each position's own E0 — required before
    # that position's loaded readings can be corrected into an Ec at all.
    unloaded_e0s: Dict[int, Decimal] = {}
    for position_no, (I, delta_l) in sorted(by_phase["unloaded"].items()):
        result = compute_tilt_unloaded_reading(accuracy_class=accuracy_class, verification_type=verification_type, e=e, I=I, delta_l=delta_l)
        unloaded_e0s[position_no] = result.E
        record_rows.append(TiltingReadingRecordOut(phase="unloaded", position_no=position_no, I=I, delta_l=delta_l, E=result.E, Ec=None))

    def loaded_rows(phase: str, load: Decimal) -> Dict[int, Decimal]:
        ecs: Dict[int, Decimal] = {}
        for position_no, (I, delta_l) in sorted(by_phase[phase].items()):
            if position_no not in unloaded_e0s:
                # Stored, but not yet scoreable — that position's own
                # unloaded reading (its E0) hasn't been submitted yet. A
                # legitimate in-progress state, not an error.
                continue
            result = compute_tilt_loaded_reading(
                accuracy_class=accuracy_class, verification_type=verification_type, e=e,
                L=load, I=I, delta_l=delta_l, E0=unloaded_e0s[position_no],
            )
            ecs[position_no] = result.Ec
            record_rows.append(TiltingReadingRecordOut(phase=phase, position_no=position_no, I=I, delta_l=delta_l, E=result.E, Ec=result.Ec))
        return ecs

    loaded_l_ecs = loaded_rows("loaded_l", L)
    loaded_max_ecs = loaded_rows("loaded_max", max_capacity)

    unloaded_check = compute_tilting_unloaded_check(e=e, position_e0s=unloaded_e0s) if REFERENCE_POSITION in unloaded_e0s else None
    loaded_l_check = (
        compute_tilting_loaded_check(accuracy_class=accuracy_class, verification_type=verification_type, e=e, L=L, position_ecs=loaded_l_ecs)
        if REFERENCE_POSITION in loaded_l_ecs else None
    )
    loaded_max_check = (
        compute_tilting_loaded_check(accuracy_class=accuracy_class, verification_type=verification_type, e=e, L=max_capacity, position_ecs=loaded_max_ecs)
        if REFERENCE_POSITION in loaded_max_ecs else None
    )

    passed = None
    if unloaded_check is not None and loaded_l_check is not None and loaded_max_check is not None:
        passed = unloaded_check.within_limit and loaded_l_check.within_mpe and loaded_max_check.within_mpe

    record_rows.sort(key=lambda row: (_PHASE_ORDER.index(row.phase), row.position_no))

    return TiltingStateOut(
        L=L,
        max_capacity=max_capacity,
        mpe_l=mpe_l,
        mpe_max=mpe_max,
        readings=record_rows,
        unloaded_max_abs_deviation=unloaded_check.max_abs_deviation if unloaded_check else None,
        unloaded_limit=unloaded_check.limit if unloaded_check else None,
        unloaded_within_limit=unloaded_check.within_limit if unloaded_check else None,
        loaded_l_max_abs_deviation=loaded_l_check.max_abs_deviation if loaded_l_check else None,
        loaded_l_within_mpe=loaded_l_check.within_mpe if loaded_l_check else None,
        loaded_max_max_abs_deviation=loaded_max_check.max_abs_deviation if loaded_max_check else None,
        loaded_max_within_mpe=loaded_max_check.within_mpe if loaded_max_check else None,
        passed=passed,
    )
