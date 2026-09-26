"""Pure Sensitivity-test orchestration: no DB, no HTTP. Mirrors the
zero-tare/discrimination service shape (build a small deterministic
check-load list, look one up by sequence_no, run the engine)."""

from dataclasses import dataclass
from decimal import Decimal

from app.contracts.instrument import InstrumentParams
from app.contracts.sensitivity import (
    SensitivityCheckOut,
    SensitivityReadingSubmitIn,
    SensitivityResultOut,
)
from engine.mpe import lookup_mpe
from engine.sensitivity import compute_sensitivity, generate_sensitivity_checks, sensitivity_threshold_mm
from engine.types import VerificationType


class SequenceNumberOutOfRange(ValueError):
    """Raised when a requested sequence_no doesn't exist in the generated
    check-load list for this instrument."""


def build_checks(instrument: InstrumentParams) -> list[Decimal]:
    return generate_sensitivity_checks(max_capacity=instrument.max_capacity, min_capacity=instrument.min_capacity)


def check_load_for_sequence_no(checks: list[Decimal], sequence_no: int) -> Decimal:
    if sequence_no < 0 or sequence_no >= len(checks):
        raise SequenceNumberOutOfRange(f"sequence_no {sequence_no} is out of range (0..{len(checks) - 1})")
    return checks[sequence_no]


def checks_with_mpe(instrument: InstrumentParams, verification_type: VerificationType) -> list[SensitivityCheckOut]:
    checks = build_checks(instrument)
    e = instrument.e_value
    threshold = sensitivity_threshold_mm(accuracy_class=instrument.accuracy_class, max_capacity=instrument.max_capacity)
    out = []
    for sequence_no, L in enumerate(checks):
        mpe_lookup = lookup_mpe(accuracy_class=instrument.accuracy_class, m=L / e, e=e, verification_type=verification_type)
        mpe = mpe_lookup.mpe_grams
        out.append(SensitivityCheckOut(sequence_no=sequence_no, L=L, mpe=mpe, extra_load=abs(mpe), threshold_mm=threshold))
    return out


@dataclass(frozen=True)
class SubmissionResult:
    L: Decimal
    result_out: SensitivityResultOut


def compute_result_for_submission(
    submission: SensitivityReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
) -> SubmissionResult:
    checks = build_checks(instrument)
    L = check_load_for_sequence_no(checks, submission.sequence_no)

    result = compute_sensitivity(
        accuracy_class=instrument.accuracy_class, verification_type=verification_type, e=instrument.e_value,
        max_capacity=instrument.max_capacity, L=L, permanent_displacement_mm=submission.permanent_displacement_mm,
    )
    result_out = SensitivityResultOut(
        L=result.L, mpe=result.mpe, extra_load=result.extra_load,
        permanent_displacement_mm=result.permanent_displacement_mm, threshold_mm=result.threshold_mm, passed=result.passed,
    )
    return SubmissionResult(L=L, result_out=result_out)
