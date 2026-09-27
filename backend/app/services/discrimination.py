"""Pure Discrimination-test orchestration: no DB, no HTTP. The sub-procedure
(`variant`) is DERIVED from the instrument's own `indication_type` — never a
client-submitted flag (the same "server derives it, nothing downstream
trusts a client-invented value" discipline as accuracy_class) — and this is
the one place that derivation happens, so the checks-GET and readings-POST
routes can never disagree about which variant applies.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.contracts.common import IndicationType
from app.contracts.discrimination import (
    DiscriminationCheckOut,
    DiscriminationReadingSubmitIn,
    DiscriminationResultOut,
    DiscriminationVariant,
)
from app.contracts.instrument import InstrumentParams
from engine.discrimination import (
    compute_discrimination_analog,
    compute_discrimination_digital,
    compute_discrimination_non_self_indicating,
    generate_discrimination_checks,
)
from engine.mpe import lookup_mpe
from engine.types import VerificationType

_VARIANT_BY_INDICATION_TYPE: dict[IndicationType, DiscriminationVariant] = {
    IndicationType.ANALOG: "analog",
    IndicationType.NON_SELF_INDICATING: "non_self_indicating",
    IndicationType.DIGITAL: "digital",
}


class SequenceNumberOutOfRange(ValueError):
    """Raised when a requested sequence_no doesn't exist in the generated
    check-load list for this instrument."""


class MissingFieldsForVariant(ValueError):
    """Raised when the submitted body is missing the field(s) this
    instrument's derived variant actually requires (e.g. `I1`/`I2` for
    analog, `visible_displacement` for non-self-indicating)."""


def variant_for_instrument(instrument: InstrumentParams) -> DiscriminationVariant:
    return _VARIANT_BY_INDICATION_TYPE[instrument.indication_type]


def build_checks(instrument: InstrumentParams) -> list[Decimal]:
    return generate_discrimination_checks(max_capacity=instrument.max_capacity, min_capacity=instrument.min_capacity)


def check_load_for_sequence_no(checks: list[Decimal], sequence_no: int) -> Decimal:
    if sequence_no < 0 or sequence_no >= len(checks):
        raise SequenceNumberOutOfRange(f"sequence_no {sequence_no} is out of range (0..{len(checks) - 1})")
    return checks[sequence_no]


def checks_with_mpe(instrument: InstrumentParams, verification_type: VerificationType) -> list[DiscriminationCheckOut]:
    checks = build_checks(instrument)
    variant = variant_for_instrument(instrument)
    e = instrument.e_value
    out = []
    for sequence_no, L in enumerate(checks):
        mpe = None
        if variant != "digital":
            mpe_lookup = lookup_mpe(accuracy_class=instrument.accuracy_class, m=L / e, e=e, verification_type=verification_type)
            mpe = mpe_lookup.mpe_grams
        out.append(DiscriminationCheckOut(sequence_no=sequence_no, L=L, mpe=mpe, variant=variant))
    return out


@dataclass(frozen=True)
class SubmissionResult:
    L: Decimal
    variant: DiscriminationVariant
    reading_data: dict
    result_out: DiscriminationResultOut


def compute_result_for_submission(
    submission: DiscriminationReadingSubmitIn,
    instrument: InstrumentParams,
    verification_type: VerificationType,
) -> SubmissionResult:
    checks = build_checks(instrument)
    L = check_load_for_sequence_no(checks, submission.sequence_no)
    variant = variant_for_instrument(instrument)

    if variant == "analog":
        if submission.I1 is None or submission.I2 is None:
            raise MissingFieldsForVariant("analog discrimination requires I1 and I2")
        result = compute_discrimination_analog(
            accuracy_class=instrument.accuracy_class, verification_type=verification_type, e=instrument.e_value,
            L=L, I1=submission.I1, I2=submission.I2,
        )
        result_out = DiscriminationResultOut(
            variant=variant, L=result.L, mpe=result.mpe, I1=result.I1, I2=result.I2,
            difference=result.difference, threshold=result.threshold, passed=result.passed,
        )
        reading_data = {"I1": str(submission.I1), "I2": str(submission.I2)}

    elif variant == "non_self_indicating":
        if submission.visible_displacement is None:
            raise MissingFieldsForVariant("non-self-indicating discrimination requires visible_displacement")
        result = compute_discrimination_non_self_indicating(
            accuracy_class=instrument.accuracy_class, verification_type=verification_type, e=instrument.e_value,
            L=L, visible_displacement=submission.visible_displacement,
        )
        result_out = DiscriminationResultOut(
            variant=variant, L=result.L, mpe=result.mpe, extra_load=result.extra_load,
            visible_displacement=result.visible_displacement, passed=result.passed,
        )
        reading_data = {"visible_displacement": submission.visible_displacement}

    else:  # digital — not required for verification (8.3.3), implemented for spec completeness
        if submission.I1 is None or submission.I2 is None:
            raise MissingFieldsForVariant("digital discrimination requires I1 and I2")
        d: Optional[Decimal] = instrument.d_value if instrument.d_value is not None else instrument.e_value
        result = compute_discrimination_digital(L=L, d=d, I1=submission.I1, I2=submission.I2)
        result_out = DiscriminationResultOut(
            variant=variant, L=result.L, d=result.d, I1=result.I1, I2=result.I2,
            difference=result.difference, passed=result.passed,
        )
        reading_data = {"I1": str(submission.I1), "I2": str(submission.I2)}

    return SubmissionResult(L=L, variant=variant, reading_data=reading_data, result_out=result_out)
