"""Tests for public abstract model contracts."""

from __future__ import annotations

import inspect
import unittest

from agent import DataRetriever
from securitized_products.cdo import CoverageTest, WaterfallEngine
from securitized_products.core import DiscountCurve, ModelContext
from securitized_products.synthetic import BaseCorrelationCalibrator


class FlatDiscountCurve(DiscountCurve):
    """Minimal concrete implementation used to test the curve contract."""

    @property
    def component_name(self) -> str:
        return "flat_discount_curve"

    def value_at(self, when, context: ModelContext) -> float:
        return self.discount_factor(when, context)

    def discount_factor(self, when, context: ModelContext) -> float:
        return 1.0


class AbstractionTests(unittest.TestCase):
    def test_public_contracts_are_abstract(self) -> None:
        abstract_classes = [
            BaseCorrelationCalibrator,
            CoverageTest,
            DataRetriever,
            DiscountCurve,
            WaterfallEngine,
        ]

        for cls in abstract_classes:
            with self.subTest(cls=cls.__name__):
                self.assertTrue(inspect.isabstract(cls))
                with self.assertRaises(TypeError):
                    cls()

    def test_minimal_concrete_curve_implementation(self) -> None:
        curve = FlatDiscountCurve()

        self.assertEqual(curve.component_name, "flat_discount_curve")
        self.assertEqual(curve.component_version, "unversioned")
        self.assertEqual(curve.discount_factor(1.0, ModelContext()), 1.0)
        self.assertEqual(curve.validate_inputs({}, ModelContext()), ())


if __name__ == "__main__":
    unittest.main()
