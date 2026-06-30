"""Abstract interfaces for cash CDO/CLO modeling components."""

from __future__ import annotations

from abc import abstractmethod
from typing import Mapping, Sequence

from securitized_products.core.abstractions import (
    ModelComponent,
    ModelContext,
    ModelPayload,
    ValidationIssue,
)


class ScheduleBuilder(ModelComponent):
    """Build model projection and liability payment schedules."""

    @abstractmethod
    def build_schedules(
        self,
        deal_terms: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return payment, accrual, reset, and projection schedules."""


class CollateralCashflowEngine(ModelComponent):
    """Project asset-level collateral cash flows."""

    @abstractmethod
    def project_collateral(
        self,
        collateral_pool: ModelPayload,
        market_data: ModelPayload,
        credit_events: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return asset-period cash flows and collateral roll-forwards."""


class ProceedsClassifier(ModelComponent):
    """Classify collateral cash into deal proceeds accounts."""

    @abstractmethod
    def classify_proceeds(
        self,
        asset_cashflows: ModelPayload,
        proceeds_mapping: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return interest, principal, reserve, hedge, and other account flows."""


class LiabilityEngine(ModelComponent):
    """Calculate liability amounts due before waterfall allocation."""

    @abstractmethod
    def calculate_liabilities(
        self,
        tranches: ModelPayload,
        fees: ModelPayload,
        hedges: ModelPayload,
        accounts: ModelPayload,
        market_data: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return note interest, fees, hedges, reserves, and balances due."""


class CollateralQualityTest(ModelComponent):
    """Collateral-quality or concentration-test contract."""

    @property
    @abstractmethod
    def test_name(self) -> str:
        """Stable test name, such as WARF, WAS, WAL, or CCC excess."""

    @abstractmethod
    def evaluate(
        self,
        collateral_state: ModelPayload,
        test_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return numerator, denominator, threshold, ratio, and pass/fail state."""


class CoverageTest(ModelComponent):
    """OC, IC, reinvestment OC, or par-value test contract."""

    @property
    @abstractmethod
    def test_name(self) -> str:
        """Stable coverage-test name."""

    @abstractmethod
    def evaluate(
        self,
        collateral_state: ModelPayload,
        liability_state: ModelPayload,
        accounts: ModelPayload,
        test_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return detailed test result and any cure amount."""


class TestEngine(ModelComponent):
    """Run all configured coverage and collateral-quality tests."""

    @abstractmethod
    def evaluate_tests(
        self,
        collateral_state: ModelPayload,
        liability_state: ModelPayload,
        accounts: ModelPayload,
        test_configs: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return period test results used by waterfalls and reinvestment."""


class WaterfallEngine(ModelComponent):
    """Apply configured priority-of-payment line items."""

    @abstractmethod
    def apply_waterfalls(
        self,
        accounts: ModelPayload,
        liability_state: ModelPayload,
        test_results: ModelPayload,
        waterfall_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return waterfall trace, account updates, and liability balance updates."""


class ReinvestmentStrategy(ModelComponent):
    """Allocate eligible principal proceeds to purchases or paydowns."""

    @abstractmethod
    def allocate_principal(
        self,
        accounts: ModelPayload,
        collateral_state: ModelPayload,
        test_results: ModelPayload,
        reinvestment_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return purchase, paydown, reserve, and blocked-cash decisions."""


class TradingStrategy(ModelComponent):
    """Generate sales, purchases, and substitutions for managed collateral."""

    @abstractmethod
    def generate_trades(
        self,
        collateral_state: ModelPayload,
        market_data: ModelPayload,
        test_results: ModelPayload,
        trading_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return proposed and executed trade activity."""


class TrancheValuationEngine(ModelComponent):
    """Value tranche cash flows and solve yield measures."""

    @abstractmethod
    def value_tranches(
        self,
        tranche_cashflows: ModelPayload,
        market_data: ModelPayload,
        valuation_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return PV, price, yield, DM, OAS, duration, and accrued interest."""


class TrancheMetricsEngine(ModelComponent):
    """Calculate tranche risk, return, and life metrics."""

    @abstractmethod
    def calculate_tranche_metrics(
        self,
        tranche_cashflows: ModelPayload,
        waterfall_trace: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return EL, PPL, PIS, PI, WAL, IRR, MOIC, and related metrics."""


class ReconciliationEngine(ModelComponent):
    """Reconcile model output to trustee reports or source/use controls."""

    @abstractmethod
    def reconcile(
        self,
        model_output: ModelPayload,
        reference_output: ModelPayload,
        tolerances: Mapping[str, float],
        context: ModelContext,
    ) -> ModelPayload:
        """Return line-item tie-out differences and pass/fail status."""


class CashCdoModel(ModelComponent):
    """Top-level institutional cash CDO/CLO engine contract."""

    @abstractmethod
    def run(
        self,
        deal_config: ModelPayload,
        collateral_pool: ModelPayload,
        market_data: ModelPayload,
        scenario_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Run the model and return typed institutional output."""

    @abstractmethod
    def validation_report(
        self,
        model_output: ModelPayload,
        context: ModelContext,
    ) -> Sequence[ValidationIssue]:
        """Return hard and soft validation findings for the completed run."""


__all__ = [
    "CashCdoModel",
    "CollateralCashflowEngine",
    "CollateralQualityTest",
    "CoverageTest",
    "LiabilityEngine",
    "ProceedsClassifier",
    "ReconciliationEngine",
    "ReinvestmentStrategy",
    "ScheduleBuilder",
    "TestEngine",
    "TradingStrategy",
    "TrancheMetricsEngine",
    "TrancheValuationEngine",
    "WaterfallEngine",
]
