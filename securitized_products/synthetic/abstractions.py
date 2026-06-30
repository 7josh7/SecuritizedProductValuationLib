"""Abstract interfaces for later synthetic CDO pricing components."""

from __future__ import annotations

from abc import abstractmethod

from securitized_products.core.abstractions import ModelComponent, ModelContext, ModelPayload


class TrancheLossModel(ModelComponent):
    """Portfolio loss and attachment/detachment tranche-loss contract."""

    @abstractmethod
    def tranche_losses(
        self,
        portfolio_losses: ModelPayload,
        tranche_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return tranche loss amounts and percentages."""


class SyntheticPricingModel(ModelComponent):
    """Price synthetic tranche cash flows or spreads."""

    @abstractmethod
    def price_tranche(
        self,
        portfolio_config: ModelPayload,
        tranche_config: ModelPayload,
        market_data: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return synthetic tranche PV, expected loss, and spread diagnostics."""


class BaseCorrelationCalibrator(ModelComponent):
    """Calibrate base-correlation curves from index-tranche quotes."""

    @abstractmethod
    def calibrate(
        self,
        index_quotes: ModelPayload,
        portfolio_config: ModelPayload,
        calibration_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Return calibrated base-correlation nodes and diagnostics."""


__all__ = [
    "BaseCorrelationCalibrator",
    "SyntheticPricingModel",
    "TrancheLossModel",
]
