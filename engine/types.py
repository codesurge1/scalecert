"""Internal dataclasses/enums for the engine. Standard library only."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional, Tuple


class AccuracyClass(str, Enum):
    I = "I"
    II = "II"
    III = "III"
    IIII = "IIII"


class VerificationType(str, Enum):
    INITIAL = "initial"
    SUBSEQUENT = "subsequent"
    IN_SERVICE = "in_service"


@dataclass(frozen=True)
class MpeResult:
    """An MPE lookup, with the band boundaries used, so it's traceable."""

    accuracy_class: AccuracyClass
    verification_type: VerificationType
    e: Decimal
    m: Decimal
    mpe_in_e: Decimal
    mpe_grams: Decimal
    band_lower_m: Decimal
    band_upper_m: Optional[Decimal]


class LoadKind(str, Enum):
    MAX = "max"
    MIN = "min"
    BAND_TRANSITION = "band_transition"
    FILL = "fill"


@dataclass(frozen=True)
class LoadEntry:
    """One load in a Weighing test's generated load sequence."""

    L: Decimal
    m: Decimal
    kind: LoadKind
    mpe: Decimal
    mpe_lookup: MpeResult

    @property
    def is_anchor(self) -> bool:
        """True for a sourced anchor (max/min/band_transition); False for a
        placeholder fill point — see engine/load_sequence.py."""
        return self.kind is not LoadKind.FILL


@dataclass(frozen=True)
class ClassificationResult:
    """The result of deriving an instrument's OIML R76-1 Table 3 accuracy
    class(es) from its e/Max/Min — see engine/classification.py. `n`
    (Max/e) is always populated, even on failure, since it's useful in a
    rejection message. `qualified_classes` is zero, one, or more classes —
    the caller decides what "more than one" means (e.g. registration
    requires the client to pick among them). `reason` explains why, only
    when `qualified_classes` is empty.
    """

    n: Decimal
    qualified_classes: Tuple[AccuracyClass, ...]
    reason: Optional[str]

    @property
    def is_valid(self) -> bool:
        return len(self.qualified_classes) > 0


@dataclass(frozen=True)
class WeighingResult:
    """The full Weighing-test derivation — never just a pass/fail verdict."""

    accuracy_class: AccuracyClass
    verification_type: VerificationType
    e: Decimal
    L: Decimal
    I: Decimal
    delta_l: Decimal
    E0: Decimal
    E: Decimal
    Ec: Decimal
    mpe: Decimal
    margin: Decimal
    passed: bool
    mpe_lookup: MpeResult
