# SecuritizedProductValuationLib Timeline

Assumption: one primary developer, starting Monday, June 22, 2026. The core cash-CDO engine and agent MVP are planned as an 8-week build. Synthetic/base-correlation work is deferred to a later phase.

## Primary Build Plan

| Week | Dates | Milestone | Deliverables |
|---|---:|---|---|
| 1 | Jun 22-26 | Project scaffold and core schemas | `pyproject.toml`, package layout, typed configs/results, seed and reproducibility conventions |
| 2 | Jun 29-Jul 3 | Academic engine MVP | Gaussian copula, default-time sampling, flat default curve, constant LGD, quarterly collateral cash flows |
| 3 | Jul 6-10 | Simple waterfall and metrics | Class A/B/equity waterfall, tranche PD/EL, undiscounted loss metrics, academic Task 1-4 reproduction |
| 4 | Jul 13-17 | Testing hardening | Golden regression tests, analytical edge cases, Monte Carlo standard errors, reproducibility tests |
| 5 | Jul 20-24 | Realistic cash structure | Term-structure PD curve, horizon selection, stochastic recovery, OC/IC triggers, shortfalls, paydowns |
| 6 | Jul 27-31 | Valuation and rating views | Discounting, tranche values, ROE/IRR, academic rating mode, agency-style approximation outputs |
| 7 | Aug 3-7 | Agent layer | Engine tool wrappers, Task-3 notional solver, data retrieval stub/cache, scenario runner |
| 8 | Aug 10-14 | Reporting and final validation | Markdown/Word-style report generation, scenario summaries, final tests, README, example notebook |

## Release Targets

| Target | Timing | Scope |
|---|---:|---|
| v0.1 | End of Week 4 | Academic cash-CDO engine working, tested, and able to reproduce the assignment outputs |
| v1.0 | End of Week 8 | Realistic cash-CDO engine with agent orchestration, scenario runs, reports, and documentation |

## Deferred Phase

| Week | Scope |
|---|---|
| 9 | QuantLib cross-check for a simplified synthetic/default-loss setup |
| 10-11 | Synthetic CDO and base-correlation module |
| 12 | Calibration examples, documentation, and cleanup |

## Notes

- The agent is built after the deterministic engine is stable.
- The academic mini-project remains a golden regression test.
- Synthetic/base-correlation pricing is intentionally separate from the v1 cash-flow engine.
