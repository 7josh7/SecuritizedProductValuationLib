# SecuritizedProductValuationLib — Architecture & Design

**Project:** `SecuritizedProductValuationLib` — a securitized-products valuation library. First product module: **CDO** (cash CDO/CLO).
**Origin:** FRE 6103 Mini-Project 3 (academic spec) → industry-grade engine + agent layer.
**Target:** A correct, testable deterministic valuation engine wrapped by a thin LLM agent for orchestration, retrieval, and reporting.
**Status:** Design doc (v2). Incorporates external review fixes. No code yet.

---

## 0. Design philosophy (read this first)

> **The math is deterministic and lives in a tested engine. The LLM never does arithmetic, never applies the waterfall, never estimates a value. The agent orchestrates the engine, retrieves inputs, runs scenarios, and explains results.**

This is also how it is done in practice: a quant library computes the loss distribution and tranche cash flows; analysts and agent tooling sit *around* it doing workflow, data sourcing, scenario design, and communication. An LLM inside the pricing loop would make results non-reproducible and unauditable — fatal for rating/valuation work.

Two layers, hard boundary:

- **Engine** (`securitized_products/`): pure functions, deterministic given a seed, fully unit-tested. Knows nothing about the LLM.
- **Agent** (`agent/`): tools that call the engine, fetch data, iterate/solve, generate narrative + reports. Consumes **typed result objects**, never raw dataframes or loose dicts.

### Library scope and naming
The library is `SecuritizedProductValuationLib`. CDO is the first product module, built on a shared core (copula, default curves, conventions, Monte Carlo, discounting) that later products (ABS, MBS, CLO) reuse. We build CDO first; we do not build the others yet, but the core is factored so they can drop in.

### The one big spine decision (resolved)
A **cash CDO/CLO** engine and a **synthetic CDO tranche** engine are different animals. v1 is unambiguously the **cash-flow spine**: coupons, recoveries, OC/IC tests, principal paydowns, residual equity — which is exactly the assignment. Synthetic/base-correlation pricing is a **separate, later mode**, not a v1 concern.

Why base correlation is deferred (and largely inapplicable here): base correlation calibrates to **liquid, standardized index-tranche quotes** (CDX/iTraxx). A bespoke bank CDO has no market quotes to calibrate against, so base correlation is a market-marking concept for *traded* tranches, not a tool for valuing this deal. It belongs in a synthetic module driven by index data, kept entirely out of the v1 cash engine.

---

## 1. The gap: academic spec vs. industry practice

The mini-project is the skeleton of the industry cash-CDO model. What we upgrade and why:

| Dimension | Academic spec | Industry-grade target | Why it matters |
|---|---|---|---|
| Default correlation | Single scalar 0.20 on "geometric" defaults | One-factor Gaussian copula; correlation enters via factor loading `a`, `ρ = a²` (latent asset correlation) | Directly correlating Bernoulli default *indicators* is not the structural-market convention and doesn't produce consistent default *timing* across horizons. A latent-variable copula does. |
| Default probability | Flat 4%/yr | Term structure of cumulative default probability `Q(t)`, calibrated to a rating | Real PDs are horizon-dependent; 5y cumulative ≠ 5 × 1y. |
| Recovery / LGD | Constant 60% LGD | Stochastic recovery (e.g. beta), `LGD = 1 − R` | Recovery dispersion materially affects tail loss and senior-tranche rating. |
| Waterfall | Senior → mezz → equity, no carry, distribute as earned | Add OC and IC tests that divert cash to deleverage senior notes when breached; interest shortfalls and paydowns | OC/IC triggers are the defining feature of real cash CDO/CLO structures. |
| Rating | Map expected loss to a Moody's Aa idealized loss rate (one lookup) | **Agency-style approximation**: EL, probability of impairment, probability of principal loss, WAL, stress metrics | Agencies run full proprietary models. We approximate the *logic*; we do not claim to reproduce their exact published criteria. |
| Pricing mode | n/a | Cash-flow valuation (v1). Synthetic base-correlation marking is a separate v2 mode | Different spines; do not conflate. |

The academic Tasks 1–5 remain a *special case* of the engine (flat curve, constant recovery, triggers off) kept as a **golden regression test**.

---

## 2. The quant math (engine spec — this is the contract)

### 2.1 One-factor Gaussian copula (the core)

Latent asset variable per obligor *i*:

```
Y_i = a · M + sqrt(1 − a²) · Z_i
```

- `M ~ N(0,1)`: systemic factor (one draw per scenario, shared by all names).
- `Z_i ~ N(0,1)`: idiosyncratic, independent across names.
- `a ∈ [0,1)`: factor loading. Pairwise **latent asset** correlation `ρ = a²`. Spec 0.20 → `a = sqrt(0.20) ≈ 0.4472`.

**Default by time t** iff `Y_i < Φ⁻¹(Q_i(t))`. Equivalently, with `U_i = Φ(Y_i)` (uniform on [0,1]), default by `t` iff `U_i < Q_i(t)`.

**Default time** (needed for the quarterly waterfall) by inverting the cumulative curve:

```
τ_i = Q_i⁻¹(U_i)
```

For constant hazard `Q(t) = 1 − e^(−λt)`:

```
τ_i = −ln(1 − U_i) / λ          # NOTE: 1 − U_i, not U_i
```

Sanity: low `Y_i` (weak credit) → low `U_i` → small `τ_i` → **early default**. (The earlier draft's `−ln(U)/λ` inverted this and is a bug; this is the corrected form.) Default within horizon `T` iff `τ_i ≤ T`, equivalently `U_i ≤ Q_i(T)`.

### 2.2 Default curve (term structure)
Cumulative default probability `Q(t)` calibrated from a rating-keyed table. The engine **selects the cumulative rate at the portfolio's horizon** (5y here), not the 1y rate — the exact judgment Task 3 warns about. Convert to hazard via `Q(t) = 1 − e^(−λt)`, or carry a piecewise-constant hazard for a full curve. Note that the geometric annual model and the constant-hazard form are identical under λ = −ln(1−p_annual).

### 2.3 Recovery / LGD
- v1 default: constant LGD = 60% (matches spec), configurable.
- Option: stochastic `R ~ Beta(α, β)` with target mean; `LGD = 1 − R`. Loss on default of name *i* = `LGD_i · Face_i`.

### 2.4 Portfolio cash flows (Task 1)
Per scenario, per quarter (20 quarters / 5y): surviving bonds pay quarterly coupon `6%/4 · Face`; survivors repay principal at maturity; a bond defaulting at `τ_i` stops coupons after `τ_i` and recognizes recovery `R_i · Face_i` at the quarter of default (timing convention, configurable). Available cash per quarter = Σ(coupons alive) + Σ(recoveries this quarter) + Σ(principal maturing & alive).

### 2.5 Waterfall (Task 2) — with OC/IC triggers
Baseline each quarter on available cash: (1) Class A interest, (2) Class B interest, (3) residual → equity.

Industry upgrade — coverage tests before the residual:
- **OC test:** `collateral_par / senior_notional`; if below trigger, divert cash to pay down Class A principal until cured.
- **IC test:** `collateral_interest / senior_interest_due`; same diversion.
- Also model **interest shortfalls** and **principal paydown** schedule. v1 ships baseline + OC/IC as a toggle so the academic answer is reproducible with triggers off.

Engine returns a `WaterfallTrace`: per-quarter cash to A/B/equity, paydown schedule, shortfalls, trigger states.

### 2.6 Tranche metrics & valuation (Task 4)
Across N Monte Carlo scenarios:
- **Probability of loss (S&P-style):** fraction of scenarios where the tranche takes any principal loss.
- **Expected loss (Moody's-style):** mean loss / notional. Spec says "do not discount" for Class B PD/EL — engine supports undiscounted metrics directly.
- **Values:** expected discounted cash flows. A discounted at risk-free + 50 bp; B at treasuries + 4%; equity from residual cash flows with a reported IRR.
- **ROE (bank):** equity cash flows ÷ retained equity, as simple return and IRR.

### 2.7 Rating — three explicit modes (agency-style *approximation*)
1. **Academic rating mode:** uses the assignment-provided cumulative default / idealized-loss thresholds; solve for the highest Class A notional whose EL stays at/below the Aa threshold (Task 3).
2. **Agency-style approximation:** reports EL, probability of impairment, probability of principal loss, WAL, and stress metrics. Explicitly *not* a reproduction of Moody's/S&P proprietary criteria.
3. **Market-pricing mode (v2, synthetic only):** base-correlation / tranche-spread calibration against index quotes. Out of scope for the cash deal.

### 2.8 Synthetic / base correlation (v2, separate module)
A synthetic-tranche module that builds the portfolio loss distribution from the copula and calibrates a base-correlation curve to standardized index-tranche quotes. Kept fully separate from the cash engine and not required for the assignment.

---

## 3. Engine vs. agent split

```
        ┌───────────────────────────── AGENT LAYER ─────────────────────────────┐
        │  parse deal terms → fetch & horizon-select default rates → drive the   │
        │  Task-3 notional solver → design/run scenario sweeps → write report &  │
        │  Task-5 rationale → explain results. Consumes typed result objects.    │
        └───────────────────────────────┬───────────────────────────────────────┘
                                         │  typed API only
        ┌───────────────────────────────▼───────────────────────────────────────┐
        │  ENGINE: copula → default times → portfolio CF → waterfall(+OC/IC) →   │
        │  tranche metrics → valuation → rating. Deterministic, seeded, tested.  │
        └───────────────────────────────────────────────────────────────────────┘
```

**Engine owns** all numerical computation. **Agent owns** input parsing, data retrieval + the horizon-selection judgment, solver orchestration (Task-3 bisection: call engine, check rating constraint, adjust bounds), scenario design, narrative, and conversation. The root-find logic itself is deterministic; the LLM decides when/why to run it and interprets the result.

---

## 4. File structure & tech stack

```
SecuritizedProductValuationLib/
├── DESIGN.md
├── README.md
├── pyproject.toml
│
├── securitized_products/
│   ├── core/                      # ── SHARED ACROSS ALL PRODUCTS ──
│   │   ├── copula.py              # one-factor Gaussian copula, default-time sampling
│   │   ├── default_curve.py       # term-structure PD, hazard calibration, horizon select
│   │   ├── recovery.py            # constant + stochastic (beta) recovery / LGD
│   │   ├── conventions.py         # day count, frequency, timing conventions (QuantLib-backed)
│   │   ├── curves.py              # discount curves (QuantLib-backed)
│   │   ├── montecarlo.py          # seeded MC driver, standard-error machinery
│   │   └── schemas.py             # typed result objects (see §4.1)
│   │
│   ├── cdo/                       # ── FIRST PRODUCT MODULE (cash CDO/CLO) ──
│   │   ├── config.py              # DealConfig, BondConfig, TrancheConfig (+ conventions)
│   │   ├── cashflows.py           # portfolio quarterly cash flows (Task 1)
│   │   ├── waterfall.py           # tranche allocation + OC/IC triggers (Task 2)
│   │   ├── metrics.py             # PD, EL, tranche loss (Task 4)
│   │   ├── valuation.py           # discounting, tranche values, ROE/IRR (Task 4)
│   │   └── rating.py              # academic + agency-style modes (Task 3)
│   │
│   └── synthetic/                 # ── v2, SEPARATE PRICING MODE ──
│       └── basecorr.py            # base-correlation calibration to index tranches
│
├── agent/
│   ├── tools.py                   # typed wrappers exposing the engine
│   ├── solvers.py                 # Task-3 notional bisection, calibration drivers
│   ├── retrieval.py               # fetch + parse default-rate tables; horizon picker
│   ├── scenarios.py               # stress/sensitivity sweeps
│   └── report.py                  # narrative + numbers → report
│
├── data/default_rates/           # cached rating-keyed cumulative default tables
├── notebooks/academic_spec_walkthrough.ipynb
├── tests/                         # see §5
└── outputs/
```

### 4.1 Typed result schemas (defined early, not bolted on)
```
SimulationResult     # raw per-scenario draws + metadata (seed, N)
ScenarioCashflows    # per-quarter collateral & tranche flows for one path
WaterfallTrace       # paydowns, shortfalls, trigger states per quarter
TrancheMetrics       # PD, EL, loss distribution, with MC error (§4.2)
ValuationResult      # values of A/B/equity, discount conventions used
RatingResult         # mode, metric values, threshold, pass/fail, solved notional
```
The agent consumes these objects, never loose dicts or pandas tables.

### 4.2 Monte Carlo error as a first-class citizen
Every headline number carries: `mean, standard_error, confidence_interval, n_scenarios, seed`. Tranche EL especially — tail estimates are noisy and the senior-tranche rating hinges on them.

### 4.3 Explicit conventions in `DealConfig` (no hidden assumptions)
`day_count`, `coupon_frequency`, `default_timing`, `recovery_timing`, `discount_curve_convention`, `principal_repayment`, `interest_shortfall_carryforward`, `writedown_vs_cash_shortfall`. Convention primitives are QuantLib-backed (see below).

### Tech stack & how we use QuantLib
- **Python 3.11+**, `numpy` (vectorized MC), `scipy` (Φ, Φ⁻¹, beta, root-finding), `pandas`, `matplotlib`/`plotly`, `pytest`.
- **QuantLib-Python — used selectively, not as the spine.** Use it directly where it is the rigorous, reinvention-is-a-liability tool: **day-count conventions, schedule/calendar generation, and discount curves** (`conventions.py`, `curves.py`), and the **`SyntheticCDO` loss-distribution engine for cross-validation** only. Do **not** route the cash waterfall, OC/IC triggers, recoveries, or equity residual through QuantLib — it does not represent those, and forcing it would distort the model. Our cash structure is our own code.

---

## 5. Validation strategy (corrected)

1. **Copula latent correlation:** empirical correlation of the *latent* variables `Y_i, Y_j` converges to `ρ = a²`. (Not default-event correlation — that's lower for low PD.)
2. **Marginal calibration:** simulated marginal default frequency per name converges to `Q(t)` at every horizon.
3. **Joint default check:** simulated *joint* default probability converges to the bivariate-normal-implied joint default probability; if comparing default-event correlation, compare to the *theoretical Bernoulli* default correlation implied by the bivariate normal, not to `ρ`.
4. **Analytical edge cases (catch more than convergence tests):**
   - 0% PD → par-like senior repayment.
   - 100% PD, 0 recovery → deterministic loss allocation.
   - 0 correlation → independence / binomial benchmark.
   - single-name portfolio → exact loss distribution.
5. **Waterfall unit tests:** hand-computed quarters, including OC/IC breach and cure, interest shortfall, paydown.
6. **Academic regression (golden):** triggers off, flat curve, constant LGD → reproduces the mini-project Task 1–4 numbers.
7. **QuantLib cross-check (narrow):** validates the synthetic/default-loss distribution and tranche-loss calculations under a matched simplified setup. **Cash waterfall behavior is validated separately via hand-computed unit tests**, since QuantLib does not model OC/IC, recoveries, or paydowns.
8. **Convergence:** MC standard error falls ≈ `1/sqrt(N)`; confidence intervals on every headline number.
9. **Agent-level verification:** a separate review pass independently re-derives Task 3's notional and confirms the rating constraint.

---

## 6. Build phases (reordered per review)

- **Phase 1 — Academic deterministic engine.** Flat default curve, constant recovery, default *times*, quarterly collateral cash flows, simple waterfall, tranche metrics. Answers Tasks 1–4 exactly.
- **Phase 2 — Testing hardening.** Golden tests, analytical edge cases, MC standard errors, seed reproducibility, result schemas locked.
- **Phase 3 — Realistic cash structure.** Term-structure PD curve + horizon selection, stochastic recovery, OC/IC triggers, interest shortfalls, principal paydowns, agency-style rating views.
- **Phase 4 — Agent layer.** Parsing, retrieval + horizon judgment, scenario orchestration, report generation, Task-3 notional solver.
- **Phase 5 — Market-pricing extras (synthetic).** Base correlation, QuantLib synthetic cross-check, calibration routines.

The agent is built only after the engine is stable — its value depends entirely on reliable engine outputs.

---

## 7. Open questions to confirm before coding

1. **Recovery timing:** recognize recovery at the quarter of default (proposed) vs. next coupon vs. maturity.
2. **Rating table source:** use the assignment's efalken cumulative-default table for the graded answer, and add a Moody's idealized-EL table as the industry alternate? (Proposed: yes to both.)
3. **Deliverable surface:** Word report + Excel model, an interactive re-runnable artifact, or both.
4. **Default-curve granularity:** single calibrated hazard (geometric, matches spec) vs. full piecewise-constant curve from the table, for v1.

---

## 8. One-paragraph summary

`SecuritizedProductValuationLib` is a securitized-products valuation library whose first module is a deterministic cash-CDO engine: a one-factor Gaussian copula with **corrected default-time sampling**, a term-structure default curve, stochastic recovery, and a trigger-aware waterfall, producing tranche PD/EL/value and ROE via Monte Carlo with first-class error reporting, typed result schemas, explicit conventions, analytical edge-case checks, and a **narrow** QuantLib cross-check of the loss distribution only. A thin LLM agent parses terms, horizon-selects default rates, drives the Task-3 solver, runs stress scenarios, and writes the report and Task-5 rationale — never touching the arithmetic. The academic mini-project is a golden regression test; base correlation and synthetic pricing are a deliberately separate later mode, because they require traded index quotes this bespoke deal does not have.
