# SecuritizedProductValuationLib

`SecuritizedProductValuationLib` is a Python project for building an auditable
securitized-products valuation engine. The first institutional target is a cash
CDO/CLO model: loan-level collateral projection, proceeds classification,
coverage tests, configurable waterfalls, valuation, scenario analysis, and
trustee-style reconciliation.

The current codebase is at the specification and interface stage. The abstract
classes define the contracts that future concrete model components must satisfy;
they do not yet implement valuation math.

## Current Status

- `MATH.md` defines the institutional quantitative contract.
- `DESIGN.md` defines the architecture and module boundaries.
- `TIMELINE.md` defines the staged build plan.
- `securitized_products/*/abstractions.py` defines abstract engine interfaces.
- `agent/abstractions.py` defines orchestration interfaces that must not perform
  valuation arithmetic.
- `tests/test_abstractions.py` verifies the public abstract contracts are
  importable and remain abstract.

## Project Structure

```text
cdo-analysis-agent/
|-- README.md
|-- DESIGN.md
|-- MATH.md
|-- TIMELINE.md
|-- clo_waterfall_model_idea.md
|-- .gitignore
|
|-- securitized_products/
|   |-- __init__.py
|   |
|   |-- core/
|   |   |-- __init__.py
|   |   `-- abstractions.py
|   |
|   |-- cdo/
|   |   |-- __init__.py
|   |   |-- abstractions.py
|   |   `-- cdo_course_proj/
|   |       |-- README.md
|   |       |-- main.py
|   |       `-- src/
|   |           |-- assets.py
|   |           |-- metrics.py
|   |           |-- portfolio.py
|   |           |-- simulation.py
|   |           |-- tranche.py
|   |           |-- valuation.py
|   |           `-- waterfall.py
|   |
|   `-- synthetic/
|       |-- __init__.py
|       `-- abstractions.py
|
|-- agent/
|   |-- __init__.py
|   `-- abstractions.py
|
|-- tests/
|   |-- __init__.py
|   `-- test_abstractions.py
|
`-- reference/
    `-- The-ABCs-of-Asset-Backed-Securities-2023 (1).pdf
```

## Layer Responsibilities

### `securitized_products.core`

Shared primitives that are not specific to cash CDOs:

- model component metadata
- run context
- validation issues
- discount, forward, and default curves
- credit and recovery models
- Monte Carlo drivers
- present-value, metric, and validation contracts

### `securitized_products.cdo`

Cash CDO/CLO engine contracts:

- schedule building
- loan-level collateral projection
- proceeds classification
- liability, fee, hedge, and reserve calculations
- collateral-quality and coverage tests
- waterfall execution
- reinvestment and trading decisions
- tranche valuation and metrics
- reconciliation and top-level cash CDO model execution

### `securitized_products.synthetic`

Later synthetic CDO pricing contracts:

- attachment/detachment tranche-loss calculations
- synthetic tranche pricing
- base-correlation calibration

This module is intentionally separate from the cash CDO/CLO waterfall engine.

### `agent`

Non-arithmetic orchestration interfaces:

- retrieve source data
- normalize source files into engine schemas
- build scenario definitions
- call deterministic engine components
- write reports
- explain typed engine outputs

The agent layer must not run valuation math, classify proceeds, apply
waterfalls, discount cash flows, allocate losses, or assign ratings.

## Abstract Class Layer

The abstract layer is a set of contracts. A concrete implementation subclasses
one of these abstract classes and implements every method marked with
`@abstractmethod`.

Example:

```python
from securitized_products.core import DiscountCurve, ModelContext


class FlatDiscountCurve(DiscountCurve):
    @property
    def component_name(self) -> str:
        return "flat_discount_curve"

    def value_at(self, when, context: ModelContext) -> float:
        return self.discount_factor(when, context)

    def discount_factor(self, when, context: ModelContext) -> float:
        return 1.0
```

`DiscountCurve` cannot be instantiated directly because it has abstract methods.
`FlatDiscountCurve` can be instantiated because it implements the required
methods.

## Development Commands

Run the abstract-contract tests:

```powershell
python -m unittest tests.test_abstractions
```

Compile Python files to catch syntax errors:

```powershell
python -m compileall securitized_products agent tests
```

Generated Python bytecode is ignored by `.gitignore`:

```text
__pycache__/
*.py[cod]
```

## Implementation Notes

- The root abstract interfaces use generic mapping payloads for now so the
  project can establish stable module boundaries before locking concrete typed
  schemas.
- Future implementation work should replace generic payloads at public seams
  with explicit dataclasses or Pydantic models.
- Every model output should include enough context to trace inputs, scenarios,
  market-data timestamps, model version, and validation status.
