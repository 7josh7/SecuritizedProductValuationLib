# CLO Cash-Flow Waterfall Model Build Idea

## 1. Goal

Build a cash-flow waterfall model for a Collateralized Loan Obligation (CLO) that projects collateral loan cash flows, applies deal-level structural rules, calculates noteholder payments, monitors coverage tests, and produces tranche-level outputs such as interest, principal, balances, losses, IRR, WAL, and break-even default metrics.

The model should answer questions such as:

- How do collateral interest and principal cash flows flow through the CLO structure?
- Are the senior and junior notes paid according to the indenture priority of payments?
- When do overcollateralization (OC), interest coverage (IC), WARF, WAL, diversity, and concentration tests pass or fail?
- How does a test failure redirect cash flow from equity/subordinated notes to senior note paydowns?
- What are the tranche-level returns under base, stress, and break-even scenarios?

---

## 2. Core Modeling Philosophy

A CLO waterfall model should be modular. Separate the model into clear engines:

1. **Collateral engine** — projects loan-level interest, amortization, prepayments, defaults, recoveries, sales, purchases, and reinvestments.
2. **Liability engine** — tracks CLO notes, coupons, spreads, benchmark rates, balances, fees, expenses, and payment seniority.
3. **Test engine** — calculates OC, IC, quality tests, collateral concentration tests, and reinvestment eligibility.
4. **Waterfall engine** — applies available interest and principal proceeds through the priority of payments.
5. **Scenario engine** — runs assumptions across default, recovery, prepayment, reinvestment, spread, and interest-rate scenarios.
6. **Output engine** — summarizes tranche cash flows, IRR, yield, WAL, losses, coverage ratios, and equity distributions.

The key principle is to keep **cash flow generation** separate from **cash flow allocation**. This makes the model easier to audit, debug, and reuse across deals.

---

## 3. Suggested Workbook or Code Architecture

### 3.1 Input Modules

#### Deal Terms

Capture all static transaction terms:

| Field | Description |
|---|---|
| Closing date | Deal start date |
| First payment date | First note distribution date |
| Payment frequency | Usually quarterly |
| Reinvestment period end | Date after which principal generally pays notes instead of reinvesting |
| Non-call period end | Earliest optional redemption date |
| Legal final maturity | Final expected/legal maturity |
| Currency | USD, EUR, etc. |
| Benchmark | SOFR, Euribor, etc. |
| Day count | 30/360, Act/360, Act/365, etc. |

#### Note Stack

Capture each tranche:

| Tranche | Initial Balance | Coupon Type | Spread / Coupon | Seniority | Rating | Notes |
|---|---:|---|---:|---:|---|---|
| Class A |  | Floating |  | 1 | AAA | Senior |
| Class B |  | Floating |  | 2 | AA | Mezzanine |
| Class C |  | Floating |  | 3 | A | Mezzanine |
| Class D |  | Floating |  | 4 | BBB | Mezzanine |
| Class E |  | Floating |  | 5 | BB | Junior |
| Subordinated Notes / Equity |  | Residual | N/A | 6 | NR | Residual |

#### Collateral Pool

At the loan level, include:

| Field | Description |
|---|---|
| Asset ID | Unique identifier |
| Issuer | Borrower / issuer name |
| Industry | Used for diversity and concentration tests |
| Country | Jurisdiction exposure |
| Rating / WARF factor | Credit quality input |
| Principal balance | Current par amount |
| Purchase price | For ramp/reinvestment modeling |
| Coupon spread | Loan spread over benchmark |
| Floor | LIBOR/SOFR floor if applicable |
| Maturity date | Asset maturity |
| Amortization type | Bullet, amortizing, scheduled repayment |
| Recovery assumption | Expected recovery after default |
| Default timing | Scenario-driven default vector |
| Prepayment / repayment assumption | Scenario-driven repayment vector |
| Cov-lite flag | If relevant for concentration tests |
| Discount obligation flag | If relevant to OC calculation |
| CCC flag | For CCC excess haircuts |

#### Scenario Inputs

Include scenario-level assumptions:

- Forward benchmark curve or flat interest-rate path.
- Annual default rate or loan-level default schedule.
- Recovery rate and recovery lag.
- Prepayment / repayment rate.
- Reinvestment spread.
- Reinvestment price.
- Reinvestment WARF / WAL / maturity constraints.
- Manager trading assumptions.
- Expense assumptions.
- Haircut rules for defaulted, discounted, CCC, long-dated, or non-performing assets.

---

## 4. Model Timeline

Create a monthly or quarterly time grid.

Common approach:

- **Monthly collateral projection** for defaults, repayments, recoveries, and reinvestment activity.
- **Quarterly waterfall dates** for actual CLO distributions.

Each period should track:

```text
Beginning collateral par
+ Purchases / reinvestments
- Scheduled amortization
- Prepayments / repayments
- Defaults
- Sales
= Ending collateral par
```

For liabilities:

```text
Beginning tranche balance
- Principal paid
- Loss allocated, if applicable
= Ending tranche balance
```

---

## 5. Collateral Cash-Flow Engine

### 5.1 Performing Loan Interest

For each performing asset:

```text
Asset coupon = max(benchmark rate, floor) + asset spread
Interest cash flow = performing balance × asset coupon × day count fraction
```

Aggregate across all performing assets:

```text
Total collateral interest = sum(asset interest cash flows)
```

### 5.2 Principal Cash Flows

Collateral principal proceeds may include:

- Scheduled amortization.
- Repayments / prepayments.
- Sale proceeds.
- Recoveries from previously defaulted assets.
- Maturity proceeds.

```text
Total principal proceeds = scheduled principal + prepayments + sales + recoveries + maturities
```

### 5.3 Defaults and Recoveries

When an asset defaults:

```text
Defaulted par = beginning performing par × default rate
Loss = defaulted par × (1 - recovery rate)
Expected recovery = defaulted par × recovery rate
```

Recoveries are usually received after a lag:

```text
Recovery cash flow at t + lag = defaulted par at t × recovery rate
```

Defaulted assets may be removed from performing collateral interest calculations immediately, unless the deal has specific rules for partial interest, defaulted interest proceeds, or sale treatment.

### 5.4 Reinvestment

During the reinvestment period, eligible principal proceeds may be used to buy new assets instead of paying down liabilities.

Simple reinvestment logic:

```text
Available reinvestment principal = eligible principal proceeds after required uses
New asset par purchased = available reinvestment principal / purchase price
```

Track new assets with assumptions for spread, rating factor, maturity, price, and prepayment/default profile.

After the reinvestment period, principal proceeds typically pay down notes sequentially, subject to deal terms.

---

## 6. Liability Cash-Flow Engine

### 6.1 Note Interest

For each floating-rate tranche:

```text
Note coupon = benchmark rate + note spread
Note interest due = beginning note balance × note coupon × day count fraction
```

For fixed-rate tranches:

```text
Note interest due = beginning note balance × fixed coupon × day count fraction
```

Track interest due, interest paid, and deferred interest if applicable.

### 6.2 Fees and Expenses

Typical deductions from interest proceeds:

1. Taxes and senior expenses.
2. Trustee, administrator, collateral manager, and other capped expenses.
3. Senior management fee.
4. Subordinated management fee, often paid later in the waterfall.
5. Incentive management fee, usually paid near the residual/equity level.

Model fees explicitly because they affect IC tests, residual equity cash flow, and note payment capacity.

---

## 7. Coverage Test Engine

Coverage tests are central to CLO waterfall behavior.

### 7.1 Overcollateralization Test

A common form:

```text
OC ratio = adjusted collateral principal amount / outstanding rated note balance
```

For a given class, the denominator usually includes that class and all classes senior to it.

```text
Class A/B OC ratio = adjusted collateral principal amount / (Class A balance + Class B balance)
```

If the OC ratio is below the required threshold, cash flow may be diverted to pay down senior notes until the test cures.

### 7.2 Interest Coverage Test

A common form:

```text
IC ratio = collateral interest proceeds / interest due on relevant notes
```

For a given class, the denominator usually includes interest due on that class and all classes senior to it.

If the IC ratio fails, interest proceeds that would otherwise go to junior tranches or equity may be redirected to principal paydowns.

### 7.3 Collateral Quality Tests

Common tests include:

- Weighted average rating factor (WARF).
- Weighted average spread (WAS).
- Weighted average life (WAL).
- Diversity score.
- CCC concentration.
- Largest obligor concentration.
- Industry concentration.
- Cov-lite concentration.
- Fixed-rate or floating-rate exposure limits.
- Long-dated asset limits.
- Discount obligation treatment.

These tests may affect reinvestment eligibility, par haircut calculations, or trading constraints.

---

## 8. Waterfall Engine

The waterfall engine is the heart of the model. It should allocate available proceeds in strict priority order.

Most CLOs have separate waterfalls for:

1. **Interest proceeds waterfall**.
2. **Principal proceeds waterfall**.
3. Sometimes special waterfalls for sale proceeds, workout assets, redemption, acceleration, or optional refinancing.

Always model based on the actual indenture, offering circular, or trustee report language.

---

## 9. Interest Proceeds Waterfall: Conceptual Order

A simplified CLO interest waterfall may look like this:

1. Pay taxes, trustee fees, administrative expenses, and senior expenses.
2. Pay Class A interest.
3. Pay Class B interest.
4. Pay Class C interest.
5. Pay Class D interest.
6. Pay Class E interest.
7. If OC/IC tests fail, divert remaining interest proceeds to pay down senior notes.
8. Pay subordinated management fee.
9. Pay deferred interest on applicable junior notes, if any.
10. Pay incentive management fee, if applicable.
11. Distribute residual to subordinated notes / equity.

Pseudo-code:

```python
available_interest = collateral_interest + other_interest_proceeds

pay(senior_expenses)
pay(class_A_interest)
pay(class_B_interest)
pay(class_C_interest)
pay(class_D_interest)
pay(class_E_interest)

if coverage_tests_fail:
    diverted_amount = available_interest
    use_as_principal_to_pay_notes_sequentially(diverted_amount)
else:
    pay(subordinated_management_fee)
    pay(deferred_interest)
    pay(incentive_fee)
    pay(equity_distribution)
```

---

## 10. Principal Proceeds Waterfall: Conceptual Order

During the reinvestment period:

1. Use principal proceeds to purchase eligible collateral.
2. Pay required note paydowns if coverage tests fail.
3. Apply special rules for defaulted asset proceeds, sales, trading gains/losses, or maturity restrictions.

After the reinvestment period:

1. Pay down Class A principal until zero.
2. Pay down Class B principal until zero.
3. Pay down Class C principal until zero.
4. Pay down Class D principal until zero.
5. Pay down Class E principal until zero.
6. Distribute remaining principal to equity.

Pseudo-code:

```python
available_principal = collateral_principal + recoveries + sale_proceeds

if within_reinvestment_period and reinvestment_tests_pass:
    reinvest(available_principal)
else:
    pay_principal_sequentially(available_principal)
```

Sequential principal paydown:

```python
for tranche in [Class_A, Class_B, Class_C, Class_D, Class_E]:
    principal_payment = min(available_principal, tranche.balance)
    tranche.balance -= principal_payment
    available_principal -= principal_payment

residual_principal_to_equity = available_principal
```

---

## 11. Diversion Logic

A key feature of CLO modeling is how failed tests redirect cash flow.

Example logic:

```text
If Class D OC test fails:
    cash otherwise available to junior notes or equity is redirected to pay down senior notes.
```

Cash is usually used to pay down the controlling class or the senior-most outstanding tranche according to the deal documents.

Modeling steps:

1. Calculate coverage tests before the waterfall.
2. Determine which tests fail.
3. Identify the applicable diversion trigger.
4. Redirect available interest or principal according to the priority of payments.
5. Recalculate ending note balances and next-period test ratios.

---

## 12. Equity Cash Flow

Equity receives residual cash after all senior obligations, fees, note interest, coverage-test diversions, and required reinvestments.

```text
Equity distribution = remaining interest proceeds + remaining principal proceeds after all senior uses
```

Track:

- Quarterly equity cash flow.
- Cumulative equity distributions.
- Equity IRR.
- Equity multiple of invested capital.
- Cash-on-cash yield.
- Sensitivity to defaults, recovery, spread, prepayments, and reinvestment assumptions.

---

## 13. Key Outputs

### Tranche-Level Outputs

For each tranche:

- Beginning balance.
- Interest due.
- Interest paid.
- Deferred interest.
- Principal paid.
- Ending balance.
- Loss allocated.
- WAL.
- Yield / IRR.
- Average life.
- Break-even default rate.

### Deal-Level Outputs

- Collateral par balance.
- Performing par balance.
- Defaulted par balance.
- Excess spread.
- OC ratios.
- IC ratios.
- WAS, WARF, WAL, diversity score.
- Reinvestment activity.
- Equity distributions.
- Total deal deleveraging.

### Scenario Outputs

- Base case.
- Rating agency stress case.
- Downside case.
- High prepayment case.
- Low recovery case.
- Spread compression case.
- Rising-rate / falling-rate cases.
- Break-even default vector by tranche.

---

## 14. Suggested Data Tables

### 14.1 `deal_terms`

```text
field_name | value | notes
```

### 14.2 `liabilities`

```text
tranche | initial_balance | current_balance | coupon_type | spread | fixed_coupon | seniority | rating | interest_deferrable
```

### 14.3 `assets`

```text
asset_id | issuer | industry | country | par | spread | floor | maturity | rating_factor | price | recovery | default_date | repayment_date
```

### 14.4 `assumptions`

```text
scenario | period | benchmark_rate | cdr | cpr | recovery_rate | recovery_lag | reinvestment_spread | reinvestment_price
```

### 14.5 `asset_cash_flows`

```text
scenario | period | asset_id | interest | scheduled_principal | prepayment | defaulted_par | recovery | sale_proceeds | ending_par
```

### 14.6 `waterfall_results`

```text
scenario | period | line_item | amount_due | amount_paid | shortfall | available_cash_after_payment
```

### 14.7 `tranche_cash_flows`

```text
scenario | period | tranche | beginning_balance | interest_due | interest_paid | principal_paid | deferred_interest | ending_balance
```

---

## 15. Implementation Roadmap

### Phase 1 — Build Static Structure

- Create deal term input table.
- Create liability stack table.
- Create collateral pool table.
- Create model date schedule.
- Set up benchmark rate assumptions.

### Phase 2 — Build Collateral Projection

- Project interest for performing assets.
- Project scheduled principal and prepayments.
- Apply defaults and remove defaulted par from performing balance.
- Apply recovery lag and recovery rate.
- Track performing par, defaulted par, recovered par, and losses.

### Phase 3 — Build Liability Projection

- Calculate note interest due.
- Track beginning and ending balances.
- Track deferred interest where applicable.
- Track fees and expenses.

### Phase 4 — Build Coverage Tests

- Calculate adjusted collateral principal amount.
- Apply haircuts for defaulted assets, CCC excess, discount obligations, and other deal-specific adjustments.
- Calculate OC ratios by class.
- Calculate IC ratios by class.
- Build pass/fail flags.

### Phase 5 — Build Waterfall

- Build interest proceeds waterfall.
- Build principal proceeds waterfall.
- Add diversion logic for failed OC/IC tests.
- Add reinvestment logic during reinvestment period.
- Add sequential paydown logic after reinvestment period.

### Phase 6 — Build Outputs and Validation

- Produce tranche cash-flow reports.
- Produce coverage-test history.
- Produce collateral balance roll-forward.
- Produce equity IRR and quarterly distributions.
- Reconcile cash sources and uses each period.
- Compare model output to trustee reports if available.

---

## 16. Validation Checks

Add checks in every period:

```text
Beginning collateral par + purchases - repayments - defaults - sales = ending collateral par
Beginning note balance - principal paid - losses = ending note balance
Total available interest - total interest uses = ending unused interest / residual
Total available principal - total principal uses = ending unused principal / residual
No tranche balance below zero
No negative available cash after waterfall line item
All waterfall cash is allocated exactly once
OC and IC test denominators match indenture definitions
```

Recommended model control flags:

- Cash leak check.
- Negative cash check.
- Negative balance check.
- Circularity check.
- Test pass/fail consistency check.
- Reinvestment eligibility check.
- Residual cash reasonableness check.

---

## 17. Common Modeling Pitfalls

1. **Mixing interest and principal proceeds incorrectly**  
   CLO documents often define interest proceeds and principal proceeds carefully. Do not freely move cash between them unless the deal allows it.

2. **Ignoring test-driven diversion**  
   Failed OC or IC tests can materially change equity cash flow and note deleveraging.

3. **Using collateral par instead of adjusted collateral par**  
   OC calculations often haircut defaulted assets, CCC excess, discount obligations, and other ineligible collateral.

4. **Forgetting deferred interest**  
   Some junior notes may defer interest. Senior notes usually cannot.

5. **Incorrect reinvestment treatment**  
   Reinvestment usually depends on eligibility criteria, timing, post-reinvestment-period rules, and coverage tests.

6. **Not modeling recovery lag**  
   Recoveries are rarely immediate. Timing affects interest proceeds, principal proceeds, and note paydowns.

7. **Not reconciling cash sources and uses**  
   Every period should have a clean cash roll-forward.

8. **Over-simplifying loan trading**  
   Trading gains/losses, discount purchases, par build/loss, and sale proceeds can affect tests and cash flow.

---

## 18. Simple End-to-End Period Flow

```text
For each payment period:

1. Start with beginning asset pool and note balances.
2. Project collateral interest.
3. Project collateral principal proceeds.
4. Apply defaults and recoveries.
5. Apply purchases, sales, and reinvestments.
6. Calculate fees and expenses.
7. Calculate note interest due.
8. Calculate OC, IC, and collateral quality tests.
9. Run interest waterfall.
10. Run principal waterfall.
11. Apply test-driven diversions.
12. Update tranche balances and deferred interest.
13. Update collateral balances.
14. Store outputs.
15. Run validation checks.
```

---

## 19. Minimal Python-Style Pseudo-Code

```python
for scenario in scenarios:
    initialize_deal(scenario)

    for period in model_periods:
        # 1. Collateral cash flows
        collateral_interest = calculate_asset_interest(assets, period, scenario)
        principal_proceeds = calculate_asset_principal(assets, period, scenario)
        defaults = apply_defaults(assets, period, scenario)
        recoveries = apply_recoveries(defaults, period, scenario)

        # 2. Liability amounts due
        note_interest_due = calculate_note_interest(notes, period, scenario)
        fees_due = calculate_fees(deal_terms, assets, notes, period)

        # 3. Coverage tests
        adjusted_collateral_par = calculate_adjusted_collateral_par(assets, deal_terms)
        oc_results = calculate_oc_tests(adjusted_collateral_par, notes, deal_terms)
        ic_results = calculate_ic_tests(collateral_interest, note_interest_due, deal_terms)
        tests_pass = evaluate_tests(oc_results, ic_results)

        # 4. Waterfalls
        interest_results = run_interest_waterfall(
            available_interest=collateral_interest,
            fees_due=fees_due,
            note_interest_due=note_interest_due,
            tests_pass=tests_pass,
            notes=notes,
        )

        principal_results = run_principal_waterfall(
            available_principal=principal_proceeds + recoveries,
            reinvestment_allowed=is_reinvestment_allowed(period, tests_pass, deal_terms),
            notes=notes,
            scenario=scenario,
        )

        # 5. Update balances
        update_assets(assets, principal_results, defaults, recoveries)
        update_notes(notes, interest_results, principal_results)

        # 6. Store and validate
        save_period_outputs(scenario, period, assets, notes, oc_results, ic_results)
        run_cash_reconciliation_checks(scenario, period)
```

---

## 20. Recommended First Version Scope

For a first working version, avoid overbuilding. Start with:

- Quarterly periods.
- Static collateral pool.
- Flat benchmark rate.
- Simple annual default vector.
- Fixed recovery rate with recovery lag.
- Simple prepayment rate.
- Sequential note paydown after reinvestment period.
- Basic OC and IC tests.
- Interest diversion if tests fail.
- Equity residual calculation.

Then add complexity:

- Loan-level trading.
- Reinvestment assets.
- Rating-factor migration.
- CCC excess haircuts.
- Discount obligation treatment.
- WAL and WARF constraints.
- Optional redemption / refinancing.
- Actual trustee report reconciliation.
- Rating-agency stress frameworks.

---

## 21. Practical Build Sequence

A good practical sequence is:

1. **Make one clean period work.**  
   Build a single-period source-and-use waterfall and reconcile cash.

2. **Extend to all periods.**  
   Roll balances forward over the full deal life.

3. **Add tests.**  
   Calculate OC/IC and make the waterfall react to failures.

4. **Add scenarios.**  
   Run default, recovery, prepayment, and spread sensitivities.

5. **Add loan-level realism.**  
   Add reinvestment, trading, recovery lag, ratings, industry constraints, and asset eligibility.

6. **Validate against real data.**  
   Compare to trustee reports, offering documents, and expected tranche behavior.

---

## 22. Final Conceptual Diagram

```text
Collateral Pool
    |
    |-- Interest proceeds ---------------------------|
    |                                                v
    |                                      Interest Waterfall
    |                                      - Expenses
    |                                      - Senior note interest
    |                                      - Junior note interest
    |                                      - Test diversion
    |                                      - Fees
    |                                      - Equity residual
    |
    |-- Principal proceeds --------------------------|
                                                     v
                                           Principal Waterfall
                                           - Reinvestment period purchases
                                           - Test-driven paydowns
                                           - Sequential note paydowns
                                           - Equity residual after notes repaid

Coverage Test Engine sits between collateral and waterfall:

Collateral data + liability balances
        |
        v
OC / IC / quality tests
        |
        v
Pass/fail flags determine whether cash flows to equity or pays down notes.
```

---

## 23. Summary

A CLO cash-flow waterfall model is mainly a structured cash allocation engine. The most important design choice is to separate collateral cash-flow generation from waterfall allocation and coverage-test logic. Once that architecture is clean, the model can be expanded from a simple base case into a full trustee-style projection engine with reinvestment, trading, rating constraints, test failures, and tranche-level stress analytics.
