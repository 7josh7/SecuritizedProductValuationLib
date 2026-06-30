"""Abstract interfaces shared by securitized-product model components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping, Sequence


YearFraction = float
ModelPayload = Mapping[str, Any]


@dataclass(frozen=True)
class ModelContext:
    """Run metadata passed through deterministic model components."""

    valuation_date: date | None = None
    scenario_id: str = "base"
    seed: int | None = None
    model_version: str = "unversioned"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationIssue:
    """A structured model validation issue."""

    code: str
    message: str
    severity: str = "error"
    location: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ModelComponent(ABC):
    """Base contract for auditable model components."""

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Stable component name for audit logs and validation output."""

    @property
    def component_version(self) -> str:
        """Semantic version or implementation identifier."""

        return "unversioned"

    def validate_inputs(
        self,
        payload: ModelPayload,
        context: ModelContext,
    ) -> Sequence[ValidationIssue]:
        """Return non-mutating input validation findings."""

        return ()


class Curve(ModelComponent):
    """Base interface for a curve or term structure."""

    @abstractmethod
    def value_at(self, when: date | YearFraction, context: ModelContext) -> float:
        """Return the curve value at a date or year fraction."""


class DiscountCurve(Curve):
    """Discount-factor curve interface."""

    @abstractmethod
    def discount_factor(
        self,
        when: date | YearFraction,
        context: ModelContext,
    ) -> float:
        """Return the discount factor from valuation date to ``when``."""


class ForwardCurve(Curve):
    """Forward-rate curve interface."""

    @abstractmethod
    def forward_rate(
        self,
        start: date | YearFraction,
        end: date | YearFraction,
        context: ModelContext,
    ) -> float:
        """Return the forward rate over an accrual period."""


class DefaultCurve(Curve):
    """Cumulative-default-probability and hazard-rate interface."""

    @abstractmethod
    def cumulative_default_probability(
        self,
        when: date | YearFraction,
        context: ModelContext,
    ) -> float:
        """Return cumulative default probability through ``when``."""

    @abstractmethod
    def hazard_rate(
        self,
        when: date | YearFraction,
        context: ModelContext,
    ) -> float:
        """Return the local or interval hazard rate at ``when``."""


class CreditModel(ModelComponent):
    """Default-time or deterministic default-vector model."""

    @abstractmethod
    def generate_defaults(
        self,
        assets: ModelPayload,
        default_curves: Mapping[str, DefaultCurve],
        context: ModelContext,
    ) -> ModelPayload:
        """Generate default events or default vectors for the collateral pool."""


class RecoveryModel(ModelComponent):
    """Recovery amount and recovery timing model."""

    @abstractmethod
    def generate_recoveries(
        self,
        defaults: ModelPayload,
        assets: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Generate recovery cash flows for defaulted assets."""


class ScenarioGenerator(ModelComponent):
    """Scenario-set generation interface."""

    @abstractmethod
    def scenarios(self, context: ModelContext) -> Iterable[ModelContext]:
        """Yield run contexts for scenario analysis."""


class MonteCarloEngine(ModelComponent):
    """Seeded simulation driver interface."""

    @abstractmethod
    def run_scenarios(
        self,
        scenario_contexts: Iterable[ModelContext],
        payload: ModelPayload,
    ) -> ModelPayload:
        """Run a collection of scenarios and return typed model output."""


class PresentValueModel(ModelComponent):
    """Present-value calculation interface."""

    @abstractmethod
    def present_value(
        self,
        cashflows: ModelPayload,
        discount_curve: DiscountCurve,
        context: ModelContext,
    ) -> ModelPayload:
        """Discount cash flows using the supplied curve and conventions."""


class MetricModel(ModelComponent):
    """Risk, return, and performance metric interface."""

    @abstractmethod
    def calculate(
        self,
        model_output: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Calculate metrics from deterministic engine output."""


class ValidationRule(ModelComponent):
    """Single validation or reconciliation rule."""

    @abstractmethod
    def validate(
        self,
        model_output: ModelPayload,
        context: ModelContext,
    ) -> Sequence[ValidationIssue]:
        """Return validation issues for a completed model output."""


__all__ = [
    "CreditModel",
    "Curve",
    "DefaultCurve",
    "DiscountCurve",
    "ForwardCurve",
    "MetricModel",
    "ModelComponent",
    "ModelContext",
    "ModelPayload",
    "MonteCarloEngine",
    "PresentValueModel",
    "RecoveryModel",
    "ScenarioGenerator",
    "ValidationIssue",
    "ValidationRule",
    "YearFraction",
]
