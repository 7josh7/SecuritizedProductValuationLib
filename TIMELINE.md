# SecuritizedProductValuationLib Timeline

Assumption: one primary developer, starting Monday, June 22, 2026. The core cash-CDO engine and agent MVP are planned as an 8-week build. Synthetic/base-correlation work is deferred to a later phase.

## Primary Build Plan

| Week | Dates | Milestone | Deliverables |
|---|---:|---|---|
| 1 | Jun 22-26 | Project scaffold and core schemas | Buildable package skeleton, typed configs/results, reproducibility conventions |
| 2 | Jun 29-Jul 3 | Academic engine MVP | Copula sampling, default-time generation, flat curve, constant LGD, collateral cash flows |
| 3 | Jul 6-10 | Simple waterfall and metrics | Class A/B/equity waterfall, tranche PD/EL, academic Task 1-4 reproduction |
| 4 | Jul 13-17 | Testing hardening | Golden tests, analytical edge cases, MC standard errors, reproducibility tests |
| 5 | Jul 20-24 | Realistic cash structure | Term-structure PD curve, stochastic recovery, OC/IC triggers, shortfalls, paydowns |
| 6 | Jul 27-31 | Valuation and rating views | Discounting, tranche values, ROE/IRR, academic rating mode, agency-style approximation outputs |
| 7 | Aug 3-7 | Agent layer | Engine tool wrappers, Task-3 notional solver, data retrieval stub/cache, scenario runner |
| 8 | Aug 10-14 | Reporting and final validation | Report generation, scenario summaries, final tests, README, example notebook |

## Detailed Weekly Tasks

### Week 1: Project Scaffold and Core Schemas

**Goal:** Create a clean, testable Python package foundation before implementing model logic.

**Tasks:**

1. Create `pyproject.toml` with package metadata, Python version, dependencies, and test tooling.
2. Create the package layout under `securitized_products/`, `securitized_products/core/`, `securitized_products/cdo/`, and `agent/`.
3. Define core config dataclasses:
   - `DealConfig`
   - `BondConfig`
   - `TrancheConfig`
   - `SimulationConfig`
4. Define typed result schemas:
   - `SimulationResult`
   - `ScenarioCashflows`
   - `WaterfallTrace`
   - `TrancheMetrics`
   - `ValuationResult`
   - `RatingResult`
5. Add package-level constants for time units, coupon frequency, and default conventions.
6. Add seed-management utilities so every simulation is reproducible.
7. Add a minimal test suite structure under `tests/`.
8. Add a smoke test that imports the package and instantiates the main config objects.
9. Add a short README section explaining how to install and run tests.

**Acceptance criteria:**

- `pip install -e .` works.
- `pytest` runs at least one passing smoke test.
- Config and result objects can be imported without circular dependencies.
- No valuation math is implemented in the agent layer.

### Week 2: Academic Engine MVP

**Goal:** Implement the deterministic academic engine pieces needed for the mini-project baseline.

**Tasks:**

1. Implement one-factor Gaussian copula sampling in `securitized_products/core/copula.py`.
2. Convert target latent correlation `rho` into factor loading `a = sqrt(rho)`.
3. Generate systemic factor `M` and idiosyncratic factors `Z_i` with a fixed seed.
4. Convert latent variables into uniform default drivers using `U_i = Phi(Y_i)`.
5. Implement constant-hazard default curve logic in `default_curve.py`.
6. Implement default-time sampling using `tau_i = -ln(1 - U_i) / lambda_i`.
7. Implement constant recovery and LGD in `recovery.py`.
8. Implement quarterly collateral cash-flow generation in `cdo/cashflows.py`.
9. Track per-name status by quarter: alive, defaulted this period, recovered, matured.
10. Return deterministic typed outputs rather than loose dictionaries.
11. Add tests for marginal default probability and default-time orientation.

**Acceptance criteria:**

- Simulated default frequency converges toward the configured cumulative default probability.
- Low `U_i` produces earlier default times, not later default times.
- Collateral coupons, recoveries, and principal repayment are produced on the quarterly grid.
- Academic assumptions can be represented: flat curve, constant LGD, no OC/IC triggers.

### Week 3: Simple Waterfall and Tranche Metrics

**Goal:** Reproduce the academic senior/mezzanine/equity structure and compute headline tranche risk metrics.

**Tasks:**

1. Implement the baseline waterfall in `cdo/waterfall.py`:
   - pay Class A interest
   - pay Class B interest
   - send residual to equity
2. Track cash paid to each tranche by quarter.
3. Track interest shortfalls even if the academic baseline does not use carryforward.
4. Implement tranche loss allocation in reverse seniority:
   - equity first
   - Class B second
   - Class A last
5. Implement expected loss in `cdo/metrics.py`.
6. Implement probability of principal loss in `cdo/metrics.py`.
7. Implement undiscounted tranche loss metrics required by the academic assignment.
8. Build an academic example configuration matching the mini-project inputs.
9. Add a notebook or script that runs Tasks 1-4 end to end.
10. Compare outputs against hand-computed small cases.

**Acceptance criteria:**

- A full academic run produces Class A, Class B, and equity cash-flow outputs.
- Expected loss and probability of loss are reported for each tranche.
- Loss allocation obeys tranche seniority in every tested scenario.
- A simple hand-computed portfolio matches the engine output exactly.

### Week 4: Testing Hardening

**Goal:** Turn the academic MVP into a reliable tested engine rather than a one-off script.

**Tasks:**

1. Add golden regression tests for the academic mini-project configuration.
2. Add analytical edge-case tests:
   - 0% default probability
   - 100% default probability with zero recovery
   - 0% LGD
   - single-name portfolio
   - zero correlation
3. Add copula tests for latent correlation convergence.
4. Add marginal default tests at multiple horizons.
5. Add joint default probability checks against the bivariate-normal result.
6. Add Monte Carlo standard error calculations.
7. Add confidence intervals to headline metrics.
8. Add seed reproducibility tests.
9. Add tests proving the same seed gives the same outputs.
10. Add tests proving different seeds change scenario draws but preserve aggregate calibration.
11. Clean up API names and module boundaries before expanding features.

**Acceptance criteria:**

- `pytest` passes for all academic and analytical tests.
- Every headline Monte Carlo metric includes scenario count, seed, standard error, and confidence interval.
- The academic implementation is stable enough to use as a golden regression baseline.
- Release `v0.1` can be tagged at the end of this week.

### Week 5: Realistic Cash Structure

**Goal:** Extend the academic model into a more realistic cash-CDO/CLO cash-flow engine.

**Tasks:**

1. Implement rating-keyed cumulative default tables under `data/default_rates/`.
2. Implement horizon selection for default curves.
3. Implement piecewise-constant hazard curves.
4. Implement stochastic recovery using a beta distribution.
5. Add recovery configuration for mean and concentration.
6. Implement OC test calculation.
7. Implement IC test calculation.
8. Implement trigger breach states in `WaterfallTrace`.
9. Implement diversion of residual cash to senior principal when OC/IC tests fail.
10. Implement senior principal paydown schedules.
11. Implement interest shortfall tracking and optional carryforward.
12. Add unit tests for trigger breach, cure, and paydown behavior.
13. Add side-by-side mode: academic triggers off vs. industry triggers on.

**Acceptance criteria:**

- Term-structure default curves replace flat default assumptions when configured.
- Stochastic recovery runs reproducibly under a fixed seed.
- OC/IC breach and cure behavior is visible in the waterfall trace.
- Turning triggers off reproduces the academic baseline.

### Week 6: Valuation and Rating Views

**Goal:** Add valuation, return, and transparent rating-style diagnostics on top of the cash-flow engine.

**Tasks:**

1. Implement discount-factor utilities in `core/curves.py`.
2. Add flat-rate discounting for initial v1 valuation.
3. Add Class A valuation at risk-free plus 50 bp.
4. Add Class B valuation at Treasury plus 400 bp.
5. Add equity residual valuation.
6. Implement equity IRR calculation.
7. Implement simple and net ROE reporting.
8. Implement academic rating mode in `cdo/rating.py`.
9. Implement Class A notional solver for the academic Aa threshold.
10. Use common random numbers inside the notional solver to reduce simulation noise.
11. Implement agency-style approximation outputs:
    - expected loss
    - probability of principal loss
    - probability of impairment
    - WAL
    - trigger breach frequency
    - shortfall frequency
12. Add tests for discounting, IRR, and rating-threshold behavior.

**Acceptance criteria:**

- Tranche values are reported with explicit discount assumptions.
- Equity IRR and ROE are labeled clearly.
- Academic rating mode can solve for the maximum Class A notional under the threshold.
- Agency-style outputs are clearly labeled as approximations, not proprietary ratings.

### Week 7: Agent Layer

**Goal:** Build the thin agent layer that orchestrates the deterministic engine without touching the math.

**Tasks:**

1. Implement typed engine wrappers in `agent/tools.py`.
2. Expose only validated engine inputs and typed result objects.
3. Implement Task-3 notional bisection orchestration in `agent/solvers.py`.
4. Implement default-rate table loading in `agent/retrieval.py`.
5. Implement horizon-selection logic for default-rate tables.
6. Implement scenario definitions in `agent/scenarios.py`.
7. Add scenario sweeps for correlation, recovery, default curve, and OC/IC triggers.
8. Implement report data assembly in `agent/report.py`.
9. Add checks ensuring agent code does not perform valuation arithmetic directly.
10. Add integration tests where the agent calls the engine and receives typed outputs.

**Acceptance criteria:**

- The agent can run the academic notional solver by calling engine functions.
- The agent can run a scenario sweep and collect typed results.
- The agent never applies the waterfall, discounts cash flows, or calculates losses itself.
- Agent outputs are reproducible when engine seeds are fixed.

### Week 8: Reporting and Final Validation

**Goal:** Package the project into a usable portfolio/research artifact.

**Tasks:**

1. Implement Markdown report generation.
2. Add optional Word/PDF export hooks if needed later.
3. Generate summary tables for tranche metrics, valuation, ROE, and rating diagnostics.
4. Generate scenario comparison tables.
5. Add charts for loss distribution, tranche losses, trigger breaches, and equity cash flows.
6. Create `notebooks/academic_spec_walkthrough.ipynb`.
7. Create a README with install, usage, model assumptions, and limitations.
8. Add a command-line entrypoint or example script for running the standard deal.
9. Run full test suite.
10. Review math against `MATH.md` and architecture against `DESIGN.md`.
11. Clean up naming, comments, and public API exports.
12. Prepare `v1.0` release notes.

**Acceptance criteria:**

- A user can install the package, run the example, and generate a report.
- README explains what the model does and does not claim to do.
- The final output clearly separates academic baseline results from industry-style extensions.
- Release `v1.0` can be tagged at the end of this week.

## Release Targets

| Target | Timing | Scope |
|---|---:|---|
| v0.1 | End of Week 4 | Academic cash-CDO engine working, tested, and able to reproduce the assignment outputs |
| v1.0 | End of Week 8 | Realistic cash-CDO engine with agent orchestration, scenario runs, reports, and documentation |

## Deferred Phase

### Week 9: QuantLib Cross-Check

**Tasks:**

1. Build a simplified synthetic/default-loss setup that can be compared with QuantLib.
2. Match portfolio assumptions between the internal engine and QuantLib as closely as possible.
3. Compare loss distributions and tranche loss metrics.
4. Document what QuantLib validates and what it does not validate.
5. Keep cash waterfall validation separate because QuantLib does not model the deal-specific OC/IC waterfall.

### Weeks 10-11: Synthetic CDO and Base Correlation

**Tasks:**

1. Create a separate synthetic module under `securitized_products/synthetic/`.
2. Implement attachment/detachment tranche loss functions.
3. Add index-tranche quote input structures.
4. Implement base-correlation calibration routines.
5. Add interpolation/extrapolation controls for the base-correlation curve.
6. Add tests using simplified synthetic examples.
7. Document why this module is separate from the cash CDO/CLO engine.

### Week 12: Calibration Examples and Cleanup

**Tasks:**

1. Add calibration examples for synthetic tranches.
2. Add documentation for assumptions, limitations, and expected inputs.
3. Add notebook examples for synthetic pricing.
4. Clean up public APIs.
5. Run final tests and prepare optional `v1.1` release notes.

## Notes

- The agent is built after the deterministic engine is stable.
- The academic mini-project remains a golden regression test.
- Synthetic/base-correlation pricing is intentionally separate from the v1 cash-flow engine.
- Every task that produces numbers must be traceable back to deterministic engine output.
