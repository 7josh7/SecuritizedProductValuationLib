# SecuritizedProductValuationLib - Architecture & Design

**Project:** `SecuritizedProductValuationLib`, a securitized-products
valuation library. First institutional product module: cash CDO/CLO.

**Origin:** FRE 6103 Mini-Project 3 academic CDO exercise.

**Target:** A deterministic, auditable institutional cash-flow engine wrapped by
a thin agent layer for data retrieval, scenario orchestration, reconciliation,
and reporting.

**Status:** Design doc v3. The math and architecture now target a full
institutional model; implementation is still at the scaffold/specification
stage.

## 0. Design Philosophy

The engine is the source of truth.

```text
LLM/agent: parse, retrieve, normalize, select scenarios, call engine, explain
engine: calculate, allocate, discount, validate, reconcile
```

The agent never samples defaults, classifies proceeds, applies a waterfall,
allocates losses, discounts cash flows, calculates ratios, or assigns ratings.
Every reported number must be traceable to typed engine output, input data
versions, market-data timestamps, scenario definitions, and model version.

This is no longer limited to the academic assignment. The assignment remains a
golden regression profile that runs with institutional features disabled.

## 1. Institutional Scope

The model targets trustee-style cash-flow projection, valuation, rating-style
stress diagnostics, and investor analytics for cash CDO/CLO transactions.

It must support:

- Loan-level collateral cash-flow projection with interest, amortization,
  prepayments, repayments, purchases, sales, defaults, recoveries, and workout
  assets.
- Separate interest proceeds, principal proceeds, reserve accounts, hedge
  accounts, and permitted account transfers.
- Full liability stack with note coupons, spreads, fees, expenses, deferrable
  interest, writedowns, writeups, and note balance roll-forwards.
- Class-specific OC and IC tests, adjusted collateral principal amount,
  collateral-quality tests, concentration tests, and reinvestment eligibility.
- Configurable interest, principal, diversion, optional redemption,
  acceleration, and special proceeds waterfalls.
- Deterministic rating-style stresses, stochastic Monte Carlo, break-even
  analysis, valuation, yield, discount margin, OAS, WAL, IRR, and equity return.
- Trustee-report tie-out mode with source/use reconciliations and tolerance
  checks.

The engine does not claim to replicate any proprietary agency, vendor, or dealer
model unless explicitly calibrated and reconciled to that model's published or
licensed methodology version.

## 2. Public Reference Anchors

The design is aligned with public structured-finance conventions:

- CLO waterfalls use separate interest and principal proceeds, senior-to-junior
  priority of payments, and test-driven diversion.
- OC tests are based on adjusted collateral balance rather than raw par.
- IC tests compare collateral interest to interest due on a class and more
  senior classes.
- Collateral-quality tests such as WARF, WAS, WAL, diversity, CCC excess, and
  concentration limits drive reinvestment and structural behavior.
- CDO tranche loss analytics use attachment/detachment, expected loss, default
  correlation, recovery assumptions, and scenario or Monte Carlo loss
  distributions.

Useful public references:

- NAIC, CLO stress tests methodology:
  `https://content.naic.org/sites/default/files/capital-markets-clo-stress-tests-methodology.pdf`
- SFA, CLO white paper:
  `https://structuredfinance.org/wp-content/uploads/2020/02/SFA-CLO-White-Paper.pdf`
- ICG, CLO primer:
  `https://www.icgam.com/wp-content/uploads/2022/02/20200603-clo-primer.pdf`
- QuantLib CDO/Synthetic CDO implementation for simplified tranche-loss
  cross-checks:
  `https://raw.githubusercontent.com/lballabio/QuantLib/master/ql/experimental/credit/cdo.hpp`

## 3. Scope Ladder

The library has three profiles.

### 3.1 Academic Profile

Used only for regression against the original coursework.

```text
flat quarterly grid
static collateral
flat default curve
constant recovery
simple A/B/equity waterfall
no reinvestment
no fees
no tests
```

### 3.2 Institutional Cash Profile

The primary production target.

```text
loan-level collateral
curves and day-count conventions
proceeds account classification
fees, expenses, hedges, and reserves
OC/IC and collateral-quality tests
reinvestment and trading rules
configurable waterfalls
valuation and rating-style stress outputs
audit/reconciliation tables
```

### 3.3 Synthetic/Market Profile

Separate module for traded synthetic tranches.

```text
portfolio default model
attachment/detachment tranche losses
index-tranche quotes
base-correlation calibration
QuantLib cross-check
```

Synthetic pricing is deliberately separate from cash CLO waterfall modeling.

## 4. Architecture

```text
agent/
  retrieval -> normalization -> scenario selection -> engine calls -> reports

securitized_products/
  core/
    calendars, day counts, curves, RNG, copulas, statistics, schemas
  cdo/
    config, collateral, credit, recoveries, proceeds, liabilities
    tests, waterfalls, reinvestment, valuation, metrics, validation
  synthetic/
    attachment/detachment, loss distributions, base correlation
```

### 4.1 Engine Flow

```text
load deal config
load collateral tape and liability stack
load curves, prices, ratings, and scenario assumptions
build date schedules
project collateral cash flows
classify proceeds into accounts
calculate fees, note interest, reserves, and hedges
calculate collateral-quality, OC, and IC tests
apply interest and principal waterfalls
apply reinvestment/trading decisions
roll forward assets, notes, accounts, and tests
validate sources/uses and balance identities
calculate valuation, risk, and return metrics
return typed results
```

### 4.2 Core Package

`securitized_products/core/`

```text
calendars.py       business-day calendars and date adjustment
daycount.py        day-count fractions and accrual conventions
curves.py          benchmark, forward, discount, DM, and OAS curves
copula.py          one-factor and multi-factor latent default models
default_curve.py   cumulative PD, hazard, and rating-table logic
recovery.py        recovery distributions and recovery-lag logic
montecarlo.py      seeded simulation driver and common random numbers
statistics.py      standard errors, confidence intervals, tail warnings
schemas.py         typed base result objects
validation.py      reusable reconciliation utilities
```

QuantLib may be used for calendars, schedules, day-count conventions, and
independent simplified synthetic CDO checks. It is not the cash waterfall spine.

### 4.3 Cash CDO/CLO Package

`securitized_products/cdo/`

```text
config.py          DealConfig, AssetConfig, TrancheConfig, TestConfig
collateral.py      loan-level interest, principal, sales, purchases, par rolls
credit.py          default vectors, copula default times, migration, watchlist
proceeds.py        proceeds classification and account transfers
liabilities.py     notes, fees, expenses, hedges, reserves, balances
tests.py           OC, IC, ACPA, WARF, WAS, WAL, concentration tests
waterfall.py       line-item waterfall execution and cash allocation
reinvestment.py    eligibility, purchases, sales, par build/loss
valuation.py       PV, price, yield, DM, OAS, clean/dirty, accrued
metrics.py         EL, PPL, PIS, PI, WAL, duration, IRR, MOIC
rating.py          academic, deterministic stress, and break-even modes
reconcile.py       trustee-report tie-out and source/use controls
examples.py        profile builders for academic and institutional examples
```

### 4.4 Agent Package

`agent/`

```text
tools.py           typed wrappers around engine functions
retrieval.py       fetch collateral tapes, curves, ratings, prices, reports
normalization.py   convert external files into engine input schemas
scenarios.py       build base/downside/rating/break-even scenario sets
solvers.py         orchestrate deterministic root-finding via engine calls
report.py          generate Markdown/Excel/Word/PDF report artifacts
explain.py         explain model outputs without recalculating them
guards.py          tests proving agent code does not perform valuation math
```

## 5. Data Model

The implementation should lock typed schemas before heavy numerical code.

### 5.1 Inputs

```text
DealConfig
ScheduleConfig
MarketDataConfig
AssetConfig
CollateralPoolConfig
TrancheConfig
FeeConfig
HedgeConfig
ReserveAccountConfig
ProceedsMappingConfig
CoverageTestConfig
CollateralQualityTestConfig
WaterfallConfig
ReinvestmentConfig
ScenarioConfig
SimulationConfig
ValuationConfig
```

### 5.2 Outputs

```text
AssetCashflowTable
ProceedsAccountTable
CoverageTestTable
CollateralQualityTestTable
WaterfallTrace
TrancheCashflowTable
BalanceRollForward
SourceUseReconciliation
ValidationReport
TrancheMetrics
ValuationResult
ScenarioComparison
RatingDiagnosticResult
BreakEvenResult
TrusteeTieOutResult
```

Outputs are typed objects with tabular export methods. The agent consumes only
these objects.

## 6. Waterfall Representation

Waterfalls must be data-driven. A deal's priority of payments is represented as
ordered line items:

```text
line_id
waterfall_name
source_account
condition
amount_due_formula
cap_formula
target
shortfall_rule
carryforward_rule
balance_update
validation_tags
```

This supports deal-specific structures without hard-coding a single indenture.
The academic waterfall is just one tiny `WaterfallConfig`.

## 7. Validation Strategy

Validation has five layers.

1. **Analytical unit tests.** Single-name loss, zero PD, full default, zero LGD,
   independent defaults, exact hand-computed waterfalls.
2. **Statistical calibration tests.** Latent correlation, marginal default
   curves, joint default probability, standard-error convergence.
3. **Cash and balance controls.** Asset par roll-forward, note roll-forward,
   account source/use, no negative cash, no overpayment, all waterfall cash used
   or reserved.
4. **Deal behavior tests.** OC/IC breach and cure, CCC excess haircut,
   discount-obligation haircut, reinvestment blocked/unblocked, deferrable
   interest, recovery lag, post-reinvestment sequential paydown.
5. **External tie-out tests.** Trustee-report actual-period reconciliation,
   vendor/rating-style benchmark cases where available, QuantLib synthetic
   tranche-loss cross-check for simplified synthetic assumptions.

Every model run emits a `ValidationReport`. A report with failed hard checks may
not be presented as final valuation output.

## 8. Tech Stack

```text
Python 3.11+
numpy
scipy
pandas
pydantic or dataclasses with explicit validation
QuantLib-Python for calendars/schedules/curves where useful
pytest
hypothesis for property tests
openpyxl/xlsxwriter for Excel review workbooks
matplotlib/plotly for report charts
```

For institutional traceability, avoid hidden pandas side effects in core engine
logic. Vectorized arrays are fine inside numerical kernels, but public results
should be typed and auditable.

## 9. Implementation Principles

- Start with schemas and reconciliation controls, not with pricing shortcuts.
- Keep cash generation, cash classification, tests, and waterfalls in separate
  modules.
- Make every deal-specific rule configurable before adding clever analytics.
- Treat failed validation as a model output, not an exception to hide.
- Keep rating-style diagnostics explicitly non-proprietary.
- Use common random numbers for comparative Monte Carlo, bisection, and
  break-even runs.
- Preserve the academic profile as a small, fast golden regression test.

## 10. Summary

`SecuritizedProductValuationLib` is now specified as a full institutional cash
CDO/CLO engine. The model projects loan-level collateral, classifies proceeds,
applies fees, reserves, tests, reinvestment constraints, and configurable
waterfalls, then produces auditable tranche cash flows, valuation, risk metrics,
rating-style diagnostics, break-even results, and trustee-report reconciliations.
The LLM agent remains outside the valuation loop and only orchestrates typed
engine calls.
