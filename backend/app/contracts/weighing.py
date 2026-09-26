"""Pydantic v2 contracts for the Weighing test — the one vertical slice built
so far (docs/plan.md Phase 2). See app/contracts/__init__.py for where the
other six test_type contracts will go later.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import Direction, StrictDecimal
from engine.types import AccuracyClass, VerificationType, WeighingResult


class WeighingReadingIn(BaseModel):
    """One Weighing-test reading, as submitted by the technician's client.

    Field provenance (this contract only validates shape; where each value
    actually comes from is a Phase 2 wiring concern, not this module's job):
      - `I`, `delta_l`: typed directly by the technician — the ONLY two
        numbers they ever enter (CLAUDE.md).
      - `L`: NOT technician-entered. Supplied by the server from the
        generated load sequence (engine.load_sequence.generate_load_sequence)
        and validated here like any other field — never a value the client
        is trusted to invent.
      - `direction`: which pass (up/down) of the bidirectional load sequence
        this reading belongs to.
      - `accuracy_class`, `e`: from the instrument record.
      - `verification_type`: from the test session.
      - `E0`: the zero-point error established earlier in this session.
    """

    model_config = ConfigDict(extra="forbid")

    accuracy_class: AccuracyClass
    verification_type: VerificationType
    direction: Direction

    e: StrictDecimal
    L: StrictDecimal = Field(
        description="Server-supplied from the generated load sequence — never technician-entered."
    )
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal


class WeighingResultOut(BaseModel):
    """The full Weighing-test derivation returned to the client — mirrors
    engine.types.WeighingResult plus the MPE band context, never just a
    pass/fail boolean (CLAUDE.md).
    """

    model_config = ConfigDict(extra="forbid")

    accuracy_class: AccuracyClass
    verification_type: VerificationType

    L: StrictDecimal
    I: StrictDecimal
    delta_l: StrictDecimal
    E0: StrictDecimal
    E: StrictDecimal
    Ec: StrictDecimal
    mpe: StrictDecimal
    margin: StrictDecimal
    passed: bool

    mpe_in_e: StrictDecimal
    band_lower_m: StrictDecimal
    band_upper_m: Optional[StrictDecimal]


def reading_to_engine_kwargs(reading: WeighingReadingIn) -> dict:
    """The engine-call seam, inbound: WeighingReadingIn -> the keyword
    arguments engine.weighing.compute_weighing_result expects. Every value on
    `reading` is already a Decimal/enum (the contract parsed it on
    construction) — this just selects the matching keywords; nothing is
    re-parsed, converted, or guessed here.
    """
    return dict(
        accuracy_class=reading.accuracy_class,
        verification_type=reading.verification_type,
        e=reading.e,
        L=reading.L,
        I=reading.I,
        delta_l=reading.delta_l,
        E0=reading.E0,
    )


def result_to_out(result: WeighingResult) -> WeighingResultOut:
    """The engine-call seam, outbound: engine.types.WeighingResult ->
    WeighingResultOut."""
    return WeighingResultOut(
        accuracy_class=result.accuracy_class,
        verification_type=result.verification_type,
        L=result.L,
        I=result.I,
        delta_l=result.delta_l,
        E0=result.E0,
        E=result.E,
        Ec=result.Ec,
        mpe=result.mpe,
        margin=result.margin,
        passed=result.passed,
        mpe_in_e=result.mpe_lookup.mpe_in_e,
        band_lower_m=result.mpe_lookup.band_lower_m,
        band_upper_m=result.mpe_lookup.band_upper_m,
    )
