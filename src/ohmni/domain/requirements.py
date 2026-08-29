"""What the user asked for, in a form the rest of the system can act on."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .component import Interface
from .evidence import Evidence
from .units import Quantity, Unit


class SafetyDomain(StrEnum):
    """Domains the MVP refuses to claim it has validated.

    Per SECURITY.md. Presence of any of these on a request is a hard stop for
    "verified" claims, not a warning to be styled in orange.
    """

    MAINS = "mains"
    LITHIUM_CHARGING = "lithium_charging"
    MEDICAL = "medical"
    AUTOMOTIVE_SAFETY = "automotive_safety"
    LIFE_SUPPORT = "life_support"
    PYROTECHNIC = "pyrotechnic"
    HIGH_CURRENT_MOTOR = "high_current_motor"
    RF_POWER_AMPLIFIER = "rf_power_amplifier"
    HIGH_VOLTAGE = "high_voltage"


class FunctionalRequirement(BaseModel):
    """One thing the board must do, tracked by id so decisions can cite it."""

    requirement_id: str
    description: str
    mandatory: bool = True


class RequirementsSpec(BaseModel):
    """The structured form of the user's request.

    Interfaces are an enum rather than free strings, because "i2c", "I2C" and
    "IIC" are the same requirement and stringly-typed comparison silently misses
    that (PRE_IMPLEMENTATION_REVIEW.md 5.6).
    """

    project_name: str
    description: str

    max_input_voltage: Quantity
    target_logic_voltage: Quantity | None = None
    budget_usd: float | None = Field(default=None, ge=0)

    max_board_layers: int = Field(default=2, ge=1, le=8)
    hand_solderable: bool = True
    min_package_pitch_mm: float | None = Field(
        default=None, gt=0, description="Smallest pitch the user is willing to hand solder."
    )

    interfaces: list[Interface] = Field(default_factory=list)
    functional_requirements: list[FunctionalRequirement] = Field(default_factory=list)
    required_part_ids: list[str] = Field(default_factory=list)
    prohibited_part_ids: list[str] = Field(default_factory=list)

    safety_domains: list[SafetyDomain] = Field(
        default_factory=list,
        description="Detected unsupported domains. Non-empty means no verified claim is possible.",
    )

    assumptions: list[str] = Field(default_factory=list)
    notes: str | None = Field(
        default=None, description="Anything the structured fields cannot express."
    )
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_units(self) -> RequirementsSpec:
        if self.max_input_voltage.unit is not Unit.VOLT:
            raise ValueError("max_input_voltage must be in volts")
        if self.target_logic_voltage is not None and self.target_logic_voltage.unit is not Unit.VOLT:
            raise ValueError("target_logic_voltage must be in volts")
        ids = [r.requirement_id for r in self.functional_requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate functional requirement ids")
        return self

    @property
    def is_supported_scope(self) -> bool:
        """MVP scope gate, per MVP_SCOPE.md: <= 12 V DC and no safety domains."""
        return not self.safety_domains and self.max_input_voltage.at_most(Quantity.volts(12.0))

    def requirement(self, requirement_id: str) -> FunctionalRequirement | None:
        for r in self.functional_requirements:
            if r.requirement_id == requirement_id:
                return r
        return None
