"""Abstract interfaces for the non-arithmetic agent layer."""

from __future__ import annotations

from abc import abstractmethod
from typing import Iterable

from securitized_products.core.abstractions import (
    ModelComponent,
    ModelContext,
    ModelPayload,
)


class DataRetriever(ModelComponent):
    """Retrieve external inputs without transforming model arithmetic."""

    @abstractmethod
    def retrieve(
        self,
        source: str,
        context: ModelContext,
    ) -> ModelPayload:
        """Fetch a source document, tape, report, curve, or market-data snapshot."""


class InputNormalizer(ModelComponent):
    """Convert external input formats into engine schemas."""

    @abstractmethod
    def normalize(
        self,
        raw_input: ModelPayload,
        target_schema: str,
        context: ModelContext,
    ) -> ModelPayload:
        """Return normalized engine input without running valuation math."""


class ScenarioBuilder(ModelComponent):
    """Build deterministic or stochastic scenario configurations."""

    @abstractmethod
    def build_scenarios(
        self,
        base_inputs: ModelPayload,
        scenario_names: Iterable[str],
        context: ModelContext,
    ) -> ModelPayload:
        """Return scenario definitions for engine execution."""


class EngineGateway(ModelComponent):
    """Typed gateway for calling deterministic engine components."""

    @abstractmethod
    def run_engine(
        self,
        engine_name: str,
        inputs: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Run a named engine function and return typed engine output."""


class ReportWriter(ModelComponent):
    """Generate reports from typed engine outputs."""

    @abstractmethod
    def write_report(
        self,
        model_output: ModelPayload,
        report_config: ModelPayload,
        context: ModelContext,
    ) -> ModelPayload:
        """Create Markdown, Excel, Word, PDF, or dashboard-ready report output."""


class OutputExplainer(ModelComponent):
    """Explain engine results without recalculating them."""

    @abstractmethod
    def explain(
        self,
        model_output: ModelPayload,
        question: str,
        context: ModelContext,
    ) -> str:
        """Return a narrative explanation backed by typed engine output."""


__all__ = [
    "DataRetriever",
    "EngineGateway",
    "InputNormalizer",
    "OutputExplainer",
    "ReportWriter",
    "ScenarioBuilder",
]
