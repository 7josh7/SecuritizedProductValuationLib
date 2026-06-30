# SecuritizedProductValuationLib Timeline

Assumption: one primary developer, starting Monday, June 22, 2026. The academic
cash-CDO exercise is still a milestone, but the target release is now a full
institutional cash CDO/CLO model with auditable waterfalls, reinvestment,
coverage tests, valuation, stress analytics, and trustee-report tie-out.

The plan is intentionally longer than the earlier v1 plan. An institutional
model needs schemas, controls, validation, and reconciliation before it is useful
or credible.

## Release Targets

| Target | Timing | Scope |
|---|---:|---|
| v0.1 | End of Week 4 | Academic regression engine: default times, basic cash flows, simple waterfall, EL/PPL |
| v0.3 | End of Week 8 | Institutional data model, schedules, curves, collateral projection, proceeds accounts |
| v0.5 | End of Week 12 | Liability stack, fees, reserves, OC/IC, collateral-quality tests, configurable waterfalls |
| v0.7 | End of Week 16 | Reinvestment, trading, recovery lags, valuation, stress, break-even analytics |
| v0.9 | End of Week 20 | Trustee-report tie-out, Excel review workbook, validation hardening |
| v1.0 | End of Week 22 | Documented institutional cash CDO/CLO release |
| v1.1+ | Deferred | Synthetic/base-correlation module and market calibration examples |

## Primary Build Plan

| Week | Dates | Milestone | Deliverables |
|---|---:|---|---|
| 1 | Jun 22-26 | Project scaffold and schemas | Package skeleton, typed configs/results, validation scaffolding |
| 2 | Jun 29-Jul 3 | Credit core | Copula, default curves, default times, recovery primitives |
| 3 | Jul 6-10 | Academic cash-flow profile | Static collateral, simple waterfall, tranche metrics |
| 4 | Jul 13-17 | Academic hardening | Golden regression, edge cases, MC errors, reproducibility |
| 5 | Jul 20-24 | Institutional schedules and curves | Calendars, day counts, payment schedules, benchmark/discount curves |
| 6 | Jul 27-31 | Loan-level collateral engine | Interest, amortization, prepayment, sales, purchases, par roll-forward |
| 7 | Aug 3-7 | Proceeds accounts | Interest/principal buckets, reserves, account transfers, source/use checks |
| 8 | Aug 10-14 | Market and collateral data normalization | Collateral tape schema, prices, ratings, eligibility flags, scenario inputs |
| 9 | Aug 17-21 | Liability stack | Notes, fees, expenses, hedges, reserves, note balance roll-forward |
| 10 | Aug 24-28 | Coverage tests | ACPA, class-specific OC/IC, WARF, WAS, WAL, concentration tests |
| 11 | Aug 31-Sep 4 | Configurable waterfalls | Interest, principal, diversion, post-reinvestment, special proceeds |
| 12 | Sep 7-11 | Waterfall validation | Hand-computed deal cases, breach/cure, shortfalls, cash controls |
| 13 | Sep 14-18 | Reinvestment engine | Eligibility, purchases, blocked reinvestment, par build/loss |
| 14 | Sep 21-25 | Trading and workout assets | Sales, credit risk/improved sales, defaulted asset treatment, recovery lags |
| 15 | Sep 28-Oct 2 | Valuation | PV, clean/dirty price, yield, DM, OAS, accrued, duration |
| 16 | Oct 5-9 | Stress and break-even analytics | Rating-style scenarios, break-even CDR/recovery/spread, scenario comparison |
| 17 | Oct 12-16 | Agent layer | Typed engine wrappers, retrieval, normalization, scenario orchestration |
| 18 | Oct 19-23 | Reporting | Markdown/Excel reports, charts, validation summaries |
| 19 | Oct 26-30 | Trustee tie-out | Actual-period reconciliation, tolerance controls, difference reports |
| 20 | Nov 2-6 | Performance and QA | Vectorization, large scenario runs, property tests, audit review |
| 21 | Nov 9-13 | Documentation and examples | README, institutional example, academic walkthrough, model limitations |
| 22 | Nov 16-20 | v1.0 release | Full test pass, release notes, package cleanup |

## Detailed Phases

### Phase 1 - Academic Regression Core (Weeks 1-4)

**Goal:** Preserve the original coursework as a small, deterministic regression
profile while building foundations that can scale.

**Tasks:**

1. Create `pyproject.toml`, package metadata, dependencies, and test tooling.
2. Create package layout under `securitized_products/core`,
   `securitized_products/cdo`, `securitized_products/synthetic`, and `agent`.
3. Define input schemas:
   - `DealConfig`
   - `ScheduleConfig`
   - `AssetConfig`
   - `CollateralPoolConfig`
   - `TrancheConfig`
   - `SimulationConfig`
   - `ScenarioConfig`
4. Define output schemas:
   - `AssetCashflowTable`
   - `WaterfallTrace`
   - `TrancheCashflowTable`
   - `TrancheMetrics`
   - `ValidationReport`
5. Implement one-factor Gaussian copula and default-time sampling.
6. Implement constant and piecewise-constant hazard curves.
7. Implement constant recovery and beta recovery primitives.
8. Implement static quarterly collateral cash flows.
9. Implement the simple academic A/B/equity waterfall.
10. Implement EL, probability of principal loss, and basic valuation hooks.
11. Add golden regression tests and analytical edge cases.
12. Add MC standard errors, seed reproducibility, and confidence intervals.

**Acceptance criteria:**

- Academic profile reproduces the original simple structure.
- Low default driver values produce earlier default times.
- Every headline Monte Carlo output includes seed, scenario count, standard
  error, and confidence interval.
- Agent package contains no valuation arithmetic.

### Phase 2 - Institutional Foundations (Weeks 5-8)

**Goal:** Build the time, curve, collateral, and proceeds infrastructure needed
for a real cash-flow model.

**Tasks:**

1. Implement calendars, business-day adjustment, payment schedules, accrual
   periods, and day-count conventions.
2. Implement benchmark forward curves and discount curves.
3. Add fixed-rate, floating-rate, floor, and fallback coupon logic.
4. Implement loan-level interest, scheduled amortization, maturity principal,
   repayments, CPR/SMM prepayments, sale proceeds, purchases, and par rolls.
5. Add defaulted asset state and recovery lag scheduling.
6. Implement proceeds classification:
   - interest proceeds
   - principal proceeds
   - hedge proceeds
   - workout proceeds
   - reserve releases
7. Implement account roll-forwards for collection, payment, reserve, and
   uninvested cash accounts.
8. Add hard source/use validation for each account.
9. Define collateral tape normalization schema with prices, ratings, industries,
   countries, spreads, floors, maturities, flags, and eligibility fields.
10. Add deterministic scenario inputs for default, recovery, prepayment, rates,
   spreads, reinvestment, and sales.

**Acceptance criteria:**

- Collateral par roll-forward balances every period.
- Account source/use reconciliations balance every period.
- The same loan can be represented as fixed, floating, amortizing, bullet,
  sold, defaulted, recovered, or reinvested.
- Proceeds classification is configured, not hard-coded inside waterfalls.

### Phase 3 - Tests, Liabilities, and Waterfalls (Weeks 9-12)

**Goal:** Model the liability side and deal structural protections with
indenture-style configurability.

**Tasks:**

1. Implement note stack with seniority, coupons, balances, deferrability, and
   interest shortfalls.
2. Implement senior expenses, trustee/admin fees, management fees, incentive
   fees, taxes, hedge payments, and reserve deposits/releases.
3. Implement note balance roll-forward with principal payments, writedowns, and
   writeups.
4. Implement adjusted collateral principal amount with component haircuts:
   - defaulted assets
   - CCC/Caa excess
   - discount obligations
   - long-dated assets
   - ineligible collateral
   - eligible cash
5. Implement class-specific OC tests.
6. Implement class-specific IC tests.
7. Implement collateral-quality tests:
   - WARF
   - WAS
   - WAL
   - diversity/concentration
   - CCC/Caa excess
   - cov-lite
   - fixed-rate and second-lien buckets
8. Implement data-driven waterfall line items.
9. Build interest, principal, diversion, and post-reinvestment waterfalls.
10. Add unit tests for OC/IC breach and cure, diversion, deferred interest,
    fee carryforward, and post-reinvestment sequential paydown.

**Acceptance criteria:**

- No waterfall logic is hard-coded to only Class A/B/equity.
- Every test result exposes numerator, denominator, threshold, ratio, pass/fail,
  shortfall/excess, and cure amount.
- Every waterfall line exposes due, paid, shortfall, carryforward, available cash
  after payment, and balance update.
- Cash and note balance controls pass for hand-computed examples.

### Phase 4 - Reinvestment, Trading, Valuation, and Stress (Weeks 13-16)

**Goal:** Add the features that materially change CLO economics and investor
analytics.

**Tasks:**

1. Implement reinvestment eligibility gates:
   - reinvestment period
   - event of default/acceleration blocks
   - reinvestment OC/par tests
   - collateral-quality tests
   - concentration tests
   - asset eligibility
2. Implement purchase of reinvestment assets at scenario price/spread/rating.
3. Implement discretionary, credit risk, and credit improved sales.
4. Track par build, par erosion, and trading gain/loss.
5. Implement recovery lag, workout assets, and sale/hold treatment for defaults.
6. Implement PV, clean/dirty price, accrued interest, yield, discount margin,
   OAS, duration, WAL, equity IRR, MOIC, and NPV.
7. Implement deterministic rating-style stress scenario sets.
8. Implement break-even solvers for CDR, cumulative default rate, recovery,
   spread compression, prepayment speed, and reinvestment price.
9. Implement Monte Carlo scenario comparison with common random numbers.

**Acceptance criteria:**

- Reinvestment can be allowed, blocked, or partially constrained based on tests.
- Trading affects cash, par, market value, and tests separately.
- Valuation outputs state cash-flow basis, curve, spread, clean/dirty treatment,
  accrued interest, and scenario mode.
- Break-even solvers use deterministic engine calls and report convergence.

### Phase 5 - Agent, Reporting, and Trustee Tie-Out (Weeks 17-20)

**Goal:** Make the model usable without weakening the engine boundary.

**Tasks:**

1. Implement typed engine wrappers in `agent/tools.py`.
2. Implement file and data retrieval in `agent/retrieval.py`.
3. Implement collateral tape, trustee report, curve, and rating normalization.
4. Implement scenario builders in `agent/scenarios.py`.
5. Implement deterministic solver orchestration in `agent/solvers.py`.
6. Add guards proving agent code does not perform valuation arithmetic.
7. Generate Markdown and Excel review workbooks.
8. Add charts for collateral balances, note balances, OC/IC ratios, test
   failures, waterfall uses, loss distributions, tranche values, and equity IRR.
9. Implement trustee-report tie-out mode:
   - actual collateral balances
   - note balances
   - interest/principal proceeds
   - waterfall line items
   - OC/IC ratios
   - cash differences by tolerance
10. Add performance profiling and large-run QA.

**Acceptance criteria:**

- Agent can run institutional scenarios only through typed engine calls.
- Reports include validation results and do not hide failed hard controls.
- Trustee tie-out produces a line-item difference report.
- Excel review workbook is sufficient for an analyst to audit major outputs.

### Phase 6 - Documentation and Release (Weeks 21-22)

**Goal:** Ship a documented institutional model with honest limits.

**Tasks:**

1. Write README install and quickstart instructions.
2. Add academic walkthrough.
3. Add institutional example with synthetic sample collateral.
4. Document all major assumptions and unsupported structures.
5. Document public references and non-proprietary rating diagnostic limits.
6. Run full test suite and performance checks.
7. Clean public APIs.
8. Prepare v1.0 release notes.

**Acceptance criteria:**

- A user can run the academic profile and institutional example.
- The model refuses or flags incomplete deal terms that would make outputs
  unreliable.
- Documentation clearly separates valuation, stress diagnostics, and rating
  claims.

## Deferred Phase - Synthetic CDO and Base Correlation

Synthetic/base-correlation work remains separate from the cash CDO/CLO engine.

**Tasks:**

1. Build a synthetic portfolio loss distribution module.
2. Implement attachment/detachment tranche losses.
3. Add standardized index-tranche quote structures.
4. Implement base-correlation calibration.
5. Add interpolation/extrapolation controls.
6. Cross-check simplified cases against QuantLib.
7. Document why this module does not drive cash CLO waterfalls.

## Notes

- The academic mini-project remains a golden regression profile.
- Institutional release quality depends on reconciliation and validation, not
  just formulas.
- Cash waterfall validation is hand-computed and trustee-report based.
- QuantLib is useful for calendars, curves, and simplified synthetic checks, not
  for deal-specific cash waterfall allocation.
- Every output must identify model version, scenario set, inputs, and validation
  status.
