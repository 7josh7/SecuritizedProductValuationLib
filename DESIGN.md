# Industry-Grade CDO Analysis Platform — Architecture & Design

**Project:** Simplified-CDO-analysis → industry-grade valuation engine + agent layer
**Origin:** FRE 6103 Mini-Project 3 (academic spec)
**Target:** A correct, testable deterministic valuation engine wrapped by a thin LLM agent for orchestration, retrieval, and reporting.
**Status:** Design doc (v1). No code yet — this defines what we build.

---

## 0. Design philosophy (read this first)

The single most important rule for this project:

> **The math is deterministic and lives in a tested Python engine. The LLM never does arithmetic, never applies the waterfall, never "estimates" a value. The agent orchestrates the engine, retrieves inputs, runs scenarios, and explains results.**

This is also how it is done in practice. On a real desk a quant library (QuantLib, internal C++/Python) computes the loss distribution and tranche cash flows; analysts and, increasingly, agent tooling sit *around* that library doing workflow, data sourcing, scenario design, and communication. Putting an LLM inside the pricing loop would make results non-reproducible and unauditable — fatal for anything rating- or valuation-related.

So everything below is split into two layers with a hard boundary between them:

- **Engine** (`cdo_engine/`): pure functions, deterministic given a seed, fully unit-tested. Knows nothing about the LLM.
- **Agent** (`cdo_agent/`): tools that call the engine, fetch data, iterate/solve, and generate narrative + reports. Knows nothing about the internals of the math beyond the engine's public API.

---

## 1. The gap: academic spec vs. industry practice

The mini-project is the skeleton of the industry model. Here is exactly what we upgrade and why.

| Dimension | Academic spec | Industry-grade target | Why it matters |
|---|---|---|---|
| Default correlation | Single scalar 0.20 applied to "geometric" defaults | One-factor Gaussian copula; correlation enters via factor loading `a` where `ρ = a²` | You cannot meaningfully correlate Bernoulli flips; you correlate the latent variables that generate default *times*. This is the market-standard model. |
| Default probability | Flat 4%/yr | Term structure of hazard rates / cumulative default curve, calibrated to a rating | Real PDs are horizon-dependent; a 5y cumulative ≠ 5 × 1y. |
| Recovery / LGD | Constant 60% LGD | Stochastic recovery (e.g. beta-distributed) with a mean; LGD = 1 − recovery | Recovery dispersion materially affects tail loss and senior-tranche rating. |
| Correlation calibration | n/a | Base correlation curve to fit multiple tranches (correlation skew) | A single flat ρ cannot fit all tranches at once; base correlation is the market convention for marking to market. |
| Waterfall | Senior → mezz → equity, no carry, distribute as earned | Add overcollateralization (OC) and interest-coverage (IC) tests that divert cash to deleverage senior notes when breached | OC/IC triggers are the defining feature of real cash CDO/CLO structures. |
| Rating | Map expected loss to a Moody's Aa idealized loss rate (one lookup) | Reproduce agency-style logic: Moody's BET / CDOROM (expected-loss based) and S&P-style Monte Carlo (probability-of-loss based) | Agencies run full models with stressed correlation, recovery distributions, and rating migration — not a one-line EL lookup. |
| Portfolio | Static, 10 names | Static now; architecture leaves room for reinvestment/amortization | Real CLOs reinvest during a window; we keep the door open but don't build it in v1. |

The academic Tasks 1–5 remain fully answerable by the engine — they become a *special case* (flat curve, constant recovery, no triggers) that we keep as a regression test to prove the engine reproduces the hand/teaching answer.

---

## 2. The quant math (engine spec)

This section is the contract the engine must satisfy. Notation kept close to standard credit references.

### 2.1 One-factor Gaussian copula (the core)

For each obligor *i*, define a latent asset-value variable:

```
X_i = a · M + sqrt(1 − a²) · Z_i
```

- `M` ~ N(0,1): common systemic factor (one draw per scenario, shared by all names).
- `Z_i` ~ N(0,1): idiosyncratic, independent across names.
- `a` ∈ [0,1): factor loading. Pairwise asset correlation is `ρ = a²`. The spec's 0.20 → `a = sqrt(0.20) ≈ 0.4472`.

Obligor *i* defaults **by time t** if `X_i < threshold_i(t)`, where the threshold is set so the marginal default probability matches the calibrated cumulative default curve:

```
threshold_i(t) = Φ⁻¹( Q_i(t) )
```

with `Q_i(t)` = cumulative probability that name *i* has defaulted by *t* (from §2.2), and Φ⁻¹ the inverse standard normal CDF.

**Default time sampling** (for cash-flow timing, needed for the waterfall): map a uniform via the survival curve. Using a constant hazard `λ` calibrated to the curve, the default time is `τ_i = −ln(U_i)/λ` where `U_i = Φ(X_i_driver)`; more generally invert the cumulative curve `Q_i`. We sample default *times* (not just yes/no) because the quarterly waterfall needs to know *when* each bond stops paying.

### 2.2 Default curve (term structure)

Replace the flat 4%/yr with a cumulative default probability `Q(t)` calibrated from a rating-keyed table (e.g. Moody's/empirical cumulative default rates). Key engine behavior:

- Input: annual marginal or cumulative default rates by horizon for the relevant rating (e.g. speculative grade).
- The engine **selects the cumulative rate at the portfolio's horizon** (5y here), not the 1y rate — this is precisely the trap Task 3 is warning about ("take the rate that matches your portfolio's duration").
- Convert to a hazard rate `λ` via `Q(t) = 1 − e^(−λt)` for the geometric/exponential default-time model, or keep the full curve for a piecewise-constant hazard.

### 2.3 Recovery / LGD

- v1: constant LGD = 60% (matches spec) as default; configurable.
- Industry option: stochastic recovery `R ~ Beta(α, β)` with `E[R] = 40%` (or 1 − 0.60), so `LGD = 1 − R`. Loss on default of name *i* = `LGD_i · FaceValue_i`.

### 2.4 Portfolio cash flows (Task 1)

Per scenario, per quarter *q* (20 quarters over 5y):

- Each surviving bond pays its quarterly coupon `= 6%/4 · Face`.
- At maturity, surviving bonds repay principal.
- A bond that defaults at `τ_i` stops paying coupons after `τ_i`; at default the structure recognizes a recovery cash inflow `= R_i · Face_i` (timing convention: at default date or next payment date — documented and configurable).
- Aggregate available cash for quarter *q* = Σ over names of (coupon if alive) + (recovery if defaulting this quarter) + (principal if maturing & alive).

### 2.5 Waterfall (Task 2) — with OC/IC triggers (industry upgrade)

Baseline (academic) waterfall, applied each quarter to available cash:

1. Pay Class A interest (coupon on A notional).
2. Pay Class B interest (coupon on B notional).
3. Residual → equity (bank).

Industry upgrade — insert coverage tests before the residual step:

- **OC test:** `OC_ratio = collateral_par / senior_notional`. If below trigger, divert cash that would go to mezz/equity to pay down Class A principal until cured.
- **IC test:** `IC_ratio = collateral_interest / senior_interest_due`. If below trigger, same diversion.
- v1 ships the baseline and OC/IC as a toggle, so the academic answer is reproducible with triggers off.

Engine returns, per scenario: full quarterly cash-flow vectors to A, B, equity; principal paydown schedule; any shortfalls.

### 2.6 Tranche metrics (Task 4)

Across N Monte Carlo scenarios:

- **PD of a tranche** = fraction of scenarios in which the tranche takes any principal loss (probability-of-loss, S&P style). Report alongside **expected loss** (EL = mean loss / notional, Moody's style). Spec says "do not discount" for the Task 4 PD/EL of Class B — engine supports undiscounted loss metrics directly.
- **Value of A, B, equity** = expected discounted cash flows. Discount A at risk-free + 50 bp (spec Task 4); B at treasuries + 4%; equity at the residual cash flows (and report an IRR). Discounting handled by a dedicated module so the discount convention is explicit and swappable.
- **ROE for the bank** = equity cash flows ÷ equity investment (residual notional retained), reported as both a simple return and an IRR.

### 2.7 Rating the tranche (Task 3 + agency-style)

- **Academic/BET-style:** compute Class A expected loss from the simulation; compare to Moody's *idealized* cumulative expected-loss rate for Aa at the 5y horizon. Solve for the **highest Class A notional** whose EL still sits at/below the Aa threshold. This is a root-find on notional → the agent's solver loop (§3.3).
- **Agency cross-check:** report both Moody's-style EL metric and S&P-style probability-of-loss metric so the user sees the methodological divergence (expected loss vs. probability of loss; BET vs. Monte Carlo).

### 2.8 Base correlation (full industry-grade)

To mark tranches to market rather than to ratings: calibrate a **base correlation curve** so the model reprices a set of standardized tranches. Implemented as a calibration routine on top of the copula loss distribution. This is the piece that captures the correlation skew. v1 exposes the hook and a single-correlation default; full calibration is a stretch module.

---

## 3. Engine vs. agent split (the architecture)

```
                 ┌─────────────────────────────────────────────┐
                 │                  AGENT LAYER                  │
                 │   (LLM: orchestration, retrieval, narrative)  │
                 │                                               │
                 │  • parse deal terms from prose / file         │
                 │  • fetch & pick default-curve rate (horizon)  │
                 │  • drive solver loops (Task 3 notional search)│
                 │  • design & run scenario / sensitivity sweeps │
                 │  • write Task 5 rationale + final report      │
                 │  • explain results, answer follow-ups         │
                 └───────────────────────┬───────────────────────┘
                                         │  calls (typed API only)
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │                 ENGINE LAYER                  │
                 │     (pure Python, deterministic, tested)      │
                 │                                               │
                 │  copula → default times → portfolio CF →      │
                 │  waterfall(+OC/IC) → tranche metrics →         │
                 │  valuation → rating map                        │
                 └─────────────────────────────────────────────┘
```

### 3.1 What the engine owns (never the LLM)
All numerical computation: copula sampling, default-time generation, cash-flow aggregation, waterfall application, Monte Carlo aggregation, discounting, PD/EL/value/ROE, rating thresholds. Deterministic given a seed. 100% unit-tested.

### 3.2 What the agent owns (genuine LLM value)
- **Input parsing:** turn a deal description (prose or a terms file) into a validated `DealConfig`.
- **Data retrieval & judgment:** fetch the rating/default-rate table, and *choose the right horizon row* for the portfolio duration — exactly the judgment Task 3 asks for.
- **Solver orchestration:** Task 3 is "largest A notional that still rates Aa." The agent runs a bisection by repeatedly calling the engine and checking the rating constraint. (The *root-find logic* can be deterministic too — the agent decides *when/why* to run it and interprets the result.)
- **Scenario design:** propose and run stress scenarios (raise correlation to 0.4, fatten LGD, flatten the curve) and summarize the sensitivity.
- **Narrative:** Task 5 ("why the bank did this structure") and the written report.
- **Conversation:** explain any number, answer "what if," regenerate the report.

### 3.3 The Task 3 solver (illustrates the boundary)
```
agent: "find max A notional keeping Class A EL ≤ Aa idealized rate"
  └─ loop (bisection on A_notional):
       engine.run_simulation(deal_with_A_notional) → A_expected_loss   [ENGINE: exact]
       compare to Aa_threshold                                         [ENGINE/util: exact]
       adjust bounds                                                    [deterministic]
  └─ agent reports the result + explains the tradeoff                  [LLM: narrative]
```
The LLM frames and explains; the numbers are all engine.

---

## 4. File structure & tech stack

```
cdo-analysis-agent/
├── DESIGN.md                      # this document
├── README.md
├── pyproject.toml                 # deps, build
│
├── cdo_engine/                    # ── DETERMINISTIC CORE ──
│   ├── __init__.py
│   ├── config.py                  # DealConfig, BondConfig, TrancheConfig (dataclasses + validation)
│   ├── copula.py                  # one-factor Gaussian copula, default-time sampling
│   ├── default_curve.py           # term-structure PD, hazard calibration, horizon selection
│   ├── recovery.py                # constant + stochastic (beta) recovery / LGD
│   ├── cashflows.py               # portfolio quarterly cash flows (Task 1)
│   ├── waterfall.py               # tranche allocation + OC/IC triggers (Task 2)
│   ├── simulation.py              # Monte Carlo driver, aggregation, seeding
│   ├── metrics.py                 # PD, EL, tranche loss (Task 4)
│   ├── valuation.py               # discounting, tranche values, ROE/IRR (Task 4)
│   ├── rating.py                  # Moody's BET / idealized-EL map, S&P-style PoL (Task 3)
│   └── basecorr.py                # base-correlation calibration (stretch)
│
├── cdo_agent/                     # ── LLM ORCHESTRATION ──
│   ├── tools.py                   # typed tool wrappers exposing the engine to the agent
│   ├── solvers.py                 # Task-3 notional bisection, calibration drivers
│   ├── retrieval.py               # fetch + parse default-rate tables; horizon picker
│   ├── scenarios.py               # stress/sensitivity sweep definitions
│   └── report.py                  # assemble narrative + numbers → report
│
├── data/
│   └── default_rates/             # cached rating-keyed cumulative default tables
│
├── notebooks/
│   └── academic_spec_walkthrough.ipynb   # reproduces Tasks 1–5 of the mini-project
│
├── tests/                         # ── PROOF THE MATH IS RIGHT ──
│   ├── test_copula.py             # correlation recovered from samples ≈ target ρ
│   ├── test_default_curve.py      # cumulative PD matches calibration at each horizon
│   ├── test_waterfall.py          # hand-computed cases, OC/IC trigger behavior
│   ├── test_valuation.py          # closed-form checks on simple deals
│   ├── test_academic_spec.py      # regression: reproduces the mini-project answers
│   └── test_convergence.py        # MC standard error shrinks ~ 1/sqrt(N)
│
└── outputs/                       # generated reports, charts
```

### Tech stack
- **Python 3.11+**, `numpy` (vectorized Monte Carlo), `scipy` (Φ, Φ⁻¹, beta, root-finding).
- **QuantLib-Python** for cross-checking tranche pricing against its `SyntheticCDO` engine (validation, not the primary path — keeps us honest).
- `pandas` for cash-flow tables, `matplotlib`/`plotly` for loss-distribution and waterfall charts.
- `pytest` for the test suite; fixed seeds for reproducibility.
- Agent tools exposed as typed functions; report output as Markdown/Word/Excel via the document skills.

### Why this stack
`numpy` vectorization makes 100k+ scenarios fast without C++. QuantLib gives an independent reference implementation so we can prove our copula/tranche math agrees with a battle-tested library — important for credibility when you claim "industry-grade."

---

## 5. Validation strategy (how we know it's right)

This is non-negotiable for anything valuation-related.

1. **Copula sanity:** empirical pairwise default correlation from samples converges to the target `ρ`.
2. **Marginal calibration:** simulated cumulative default frequency per name matches `Q(t)` at every horizon.
3. **Waterfall unit tests:** hand-computed quarters, including OC/IC breach and cure.
4. **Academic regression:** with triggers off, flat curve, constant LGD, the engine reproduces the mini-project's Task 1–4 numbers (these become golden values).
5. **Independent cross-check:** tranche EL/value vs. QuantLib `SyntheticCDO` on a matched setup.
6. **Convergence:** Monte Carlo standard error falls ≈ `1/sqrt(N)`; report confidence intervals on every headline number.
7. **Agent-level verification:** a separate review pass (sub-agent or checklist) re-derives Task 3's notional independently and confirms the rating constraint holds.

---

## 6. Build phases

- **Phase 1 — Engine MVP (reproduce the spec).** copula + flat curve + portfolio CF + baseline waterfall + metrics + valuation. Pass `test_academic_spec`. Answers Tasks 1–4 exactly.
- **Phase 2 — Industry realism.** term-structure default curve + horizon selection, stochastic recovery, OC/IC triggers, Moody's-EL and S&P-PoL rating views. Task 3 solver.
- **Phase 3 — Agent layer.** tools, retrieval + horizon judgment, scenario sweeps, report generation, Task 5 narrative.
- **Phase 4 — Full industry-grade extras.** base-correlation calibration, QuantLib cross-check, stochastic recovery distributions, optional reinvestment hook.

Each phase is independently useful and testable. Phase 1 alone already satisfies the assignment; everything after is the "industry-grade" upgrade you asked for.

---

## 7. Open questions / decisions to confirm before coding

1. **Default-time vs. one-period default:** I propose sampling default *times* (needed for the quarterly waterfall and OC/IC timing). Confirm you want quarter-level timing rather than a single 5y default indicator.
2. **Recovery timing convention:** recovery cash recognized at default date vs. next coupon date vs. maturity — affects discounting slightly. Propose: at the quarter of default.
3. **Rating table source:** the assignment links a specific cumulative-default-rate table (efalken.com). For industry-grade we'd prefer a Moody's idealized-EL table; confirm whether to use the assignment's source for the graded answer and add the agency table as an alternate.
4. **Deliverable surface for the agent:** report as Word + Excel model, or an interactive artifact (live, re-runnable) — or both.

---

## 8. One-paragraph summary

We build a deterministic Python valuation engine that models the portfolio with a one-factor Gaussian copula, a term-structure default curve, stochastic recovery, and a trigger-aware waterfall, producing tranche PD/EL/value and ROE via Monte Carlo with full test coverage and a QuantLib cross-check. Around it sits a thin LLM agent that parses deal terms, retrieves and correctly horizon-selects default rates, drives the Task-3 notional solver, runs stress scenarios, and writes the report and the Task-5 rationale. The academic mini-project becomes a regression test; the industry upgrades (copula, base correlation, OC/IC triggers, agency-style rating) are what make it realistic. The LLM never touches the arithmetic — that is the whole point, and it is also how this is done on a real desk.
