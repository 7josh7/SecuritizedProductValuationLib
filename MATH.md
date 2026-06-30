# SecuritizedProductValuationLib Math Specification

This file is the quantitative contract for the first institutional cash CDO/CLO
model in `SecuritizedProductValuationLib`. The model is a deterministic,
auditable engine given its inputs, market data, scenario definitions, and random
seed. The agent layer may select inputs, run scenarios, and explain results, but
it must not perform valuation arithmetic.

The academic mini-project remains a special configuration:

```text
static collateral pool
quarterly grid
flat default probability
constant recovery
no fees
no reinvestment
no collateral-quality tests
single senior/mezz/equity waterfall
```

The institutional model generalizes that case into a trustee-style and
rating-diagnostic cash-flow engine. It does not claim to reproduce proprietary
Moody's, S&P, Fitch, KBRA, Intex, Bloomberg, or CDONet outputs unless explicitly
calibrated and reconciled to a deal, trustee report, and methodology version.

GitHub renders the formulas in this document as LaTeX math.

## 1. Modeling Standard

The model must satisfy five institutional requirements.

1. **Indenture fidelity.** Every cash movement is driven by configured deal terms:
   dates, accounts, proceeds definitions, fees, note coupons, coverage tests,
   collateral-quality tests, reinvestment rules, and priority of payments.
2. **Separate generation and allocation.** Collateral cash-flow generation is
   independent from waterfall allocation. No collateral engine function may know
   tranche seniority, and no waterfall function may synthesize collateral cash.
3. **Separate proceeds accounts.** Interest proceeds, principal proceeds,
   trading proceeds, recoveries, workout proceeds, reserve releases, and amounts
   permitted to cross between accounts are tracked explicitly.
4. **Auditability.** Every period has source/use reconciliations, balance
   roll-forwards, test numerator/denominator detail, line-item shortfalls, and
   reproducible scenario metadata.
5. **Mode transparency.** The engine supports base-case valuation, deterministic
   rating stresses, stochastic Monte Carlo risk metrics, break-even analysis, and
   historical/trustee-report tie-out as separate modes.

## 2. Notation

| Symbol | Meaning |
|---|---|
| $i$ | Collateral asset or obligor index |
| $j$ | Liability tranche index |
| $q$ | Payment period index |
| $m$ | Collateral projection period index, often monthly |
| $t$ | Time in years |
| $T$ | Deal horizon or legal final maturity |
| $F_{i,t}$ | Asset par or funded balance |
| $UPB_{i,t}$ | Unpaid principal balance |
| $P_i$ | Purchase price as percent of par |
| $S_i$ | Sale price as percent of par |
| $s_i$ | Asset spread over benchmark |
| $f_i$ | Asset index floor |
| $c_i(t)$ | Asset coupon rate |
| $N_{j,t}$ | Tranche notional outstanding |
| $r_j(t)$ | Tranche coupon rate |
| $Q_i(t)$ | Cumulative default probability for name $i$ |
| $\lambda_i(t)$ | Hazard rate for name $i$ |
| $R_i$ | Recovery rate |
| $LGD_i$ | Loss given default, $1 - R_i$ |
| $\tau_i$ | Default time |
| $\ell_i$ | Recovery lag |
| $\rho$ | Pairwise latent asset correlation |
| $a$ | One-factor loading, where $\rho = a^2$ |
| $M$ | Systematic factor |
| $Z_i$ | Idiosyncratic factor |
| $Y_i$ | Latent asset variable |
| $DF(t)$ | Discount factor to time $t$ |
| $IP_q$ | Interest proceeds available on payment date $q$ |
| $PP_q$ | Principal proceeds available on payment date $q$ |
| $ACPA_q$ | Adjusted collateral principal amount |
| $OC_{k,q}$ | Overcollateralization ratio for test class $k$ |
| $IC_{k,q}$ | Interest coverage ratio for test class $k$ |

## 3. Time Grid, Calendars, and Accrual

The engine supports two grids:

```text
collateral projection grid: monthly or asset-event dates
liability payment grid: usually quarterly
```

Let payment dates be $D_q$ and previous payment dates be $D_{q-1}$. The year
fraction for a cash-flow item is:

$$
\Delta_{x,q} = \operatorname{DCF}(D_{q-1}, D_q; \operatorname{daycount}_x)
$$

where $x$ can be an asset, tranche, fee, hedge, or reserve account. Business-day
adjustment, holiday calendar, end-of-month behavior, payment delays, and reset
dates are part of `DealConfig`.

Required date fields:

```text
closing_date
effective_date
first_payment_date
payment_dates
reinvestment_period_end
non_call_period_end
weighted_average_life_test_date
stated_maturity
legal_final_maturity
optional_redemption_dates
```

The academic mode may collapse this to:

$$
\Delta = 0.25,\qquad t_q = q\Delta
$$

## 4. Market Curves and Coupon Rates

### 4.1 Benchmark Curve

Each scenario has a benchmark forward curve or rate path:

$$
I_q = \operatorname{IndexRate}(D_{q-1}, D_q)
$$

Examples include SOFR, Term SOFR, Euribor, SONIA, or a flat academic rate.
Curve interpolation, compounding conventions, observation shifts, lookbacks,
fallback rates, and index floors must be configured explicitly.

### 4.2 Asset Coupon

For a floating-rate loan:

$$
c_{i,q} = \max(I_q, f_i) + s_i
$$

If an asset is fixed-rate:

$$
c_{i,q} = c_i^{fixed}
$$

Asset interest before default adjustments is:

$$
\operatorname{AssetInterest}_{i,q}
= \operatorname{PerformingBalance}_{i,q-1}
  c_{i,q}\Delta_{i,q}
$$

The engine must support non-cash pay, PIK, delayed-draw, revolving, fixed-rate,
discount, defaulted, and workout assets through explicit asset type flags.

### 4.3 Note Coupon

For floating-rate liabilities:

$$
r_{j,q} = I_q + spread_j
$$

For fixed-rate liabilities:

$$
r_{j,q} = r_j^{fixed}
$$

Interest due is:

$$
I^{due}_{j,q}
= N_{j,q-1} r_{j,q}\Delta_{j,q}
+ \operatorname{DeferredInterest}_{j,q-1}
+ \operatorname{DefaultedInterestPenalty}_{j,q}
$$

Interest deferral eligibility is class-specific. Senior classes typically require
timely interest; junior deferrable notes may carry forward unpaid interest.

## 5. Credit Model

The engine supports deterministic and stochastic credit modes.

### 5.1 Deterministic Default Vectors

Rating-style and scenario runs may provide asset-level or portfolio-level default
amounts by period. If $CDR_m$ is an annualized conditional default rate and
$\Delta_m$ is the year fraction for the projection period, convert it to a
period default rate:

$$
p_m^{default}=1-(1-CDR_m)^{\Delta_m}
$$

then:

$$
\operatorname{DefaultedPar}_{m}
= \operatorname{PerformingPar}_{m-1} \cdot p_m^{default}
$$

or explicit asset default dates:

```text
asset_id | default_date | recovery_rate | recovery_date | sale_price
```

Deterministic default vectors are required for rating stresses, break-even CDR,
trustee-report tie-outs, and analyst-defined downside cases.

### 5.2 One-Factor Gaussian Copula

Each obligor has a latent variable:

$$
Y_i = aM + \sqrt{1-a^2}Z_i
$$

with:

$$
M \sim N(0,1),\qquad Z_i \sim N(0,1)
$$

and:

$$
\operatorname{Corr}(Y_i,Y_k) = a^2 = \rho
$$

Define:

$$
U_i = \Phi(Y_i)
$$

Then name $i$ defaults by time $t$ if:

$$
U_i \le Q_i(t)
$$

Equivalently:

$$
Y_i \le \Phi^{-1}(Q_i(t))
$$

### 5.3 Multi-Factor Extension

Institutional portfolios may require industry, region, sponsor, or rating
factors:

$$
Y_i = \sum_{g=1}^{G} a_{i,g}M_g
      + \sqrt{1-\sum_{g=1}^{G}a_{i,g}^2}Z_i
$$

with:

$$
\sum_{g=1}^{G}a_{i,g}^2 \le 1
$$

The one-factor model remains the default because it is transparent and stable.
The multi-factor model is optional and must report the full loading matrix.

### 5.4 Default-Time Sampling

Default times are generated by inverse transform:

$$
\tau_i = Q_i^{-1}(U_i)
$$

For a constant hazard:

$$
Q_i(t) = 1 - e^{-\lambda_i t}
$$

so:

$$
\tau_i = \frac{-\ln(1-U_i)}{\lambda_i}
$$

Low latent credit quality gives low $U_i$, which gives early default. The formula
$-\ln(U_i)/\lambda_i$ is invalid for this construction because it reverses the
ordering.

### 5.5 Piecewise-Constant Hazard Curve

For default tenors:

$$
0=T_0<T_1<\cdots<T_K
$$

and cumulative default probabilities $Q(T_k)$:

$$
S(T_k)=1-Q(T_k)
$$

The interval hazard is:

$$
\lambda_k =
\frac{-\ln(S(T_k)/S(T_{k-1}))}{T_k-T_{k-1}}
$$

For $t\in(T_{k-1},T_k]$:

$$
S(t)=S(T_{k-1})e^{-\lambda_k(t-T_{k-1})}
$$

$$
Q(t)=1-S(t)
$$

To invert the curve, find the first interval where:

$$
Q(T_{k-1}) < U_i \le Q(T_k)
$$

then:

$$
\tau_i =
T_{k-1}
- \frac{\ln((1-U_i)/S(T_{k-1}))}{\lambda_k}
$$

If $U_i > Q(T_K)$, the name survives beyond the last curve tenor.

### 5.6 Rating Migration and Watchlist State

The base model may hold ratings static. The institutional model must support
optional migration:

```text
current_rating -> migrated_rating
rating_factor(current_rating) -> rating_factor(migrated_rating)
CCC flag
default probability curve update
recovery assumption update
eligibility impact
```

Migration can be deterministic by scenario or stochastic using a transition
matrix. Rating migration affects WARF, CCC excess, default curves, recoveries,
eligibility, and concentration tests.

## 6. Recovery, Workouts, and Defaulted Assets

### 6.1 Recovery Timing

Recoveries are not immediate unless the deal or scenario explicitly says so. If
asset $i$ defaults at $\tau_i$, recovery is received at:

$$
\operatorname{RecoveryDate}_i = \tau_i + \ell_i
$$

where $\ell_i$ can be fixed, rating/asset-type specific, scenario-specific, or
random. Recovery cash is recognized in the first proceeds period containing the
recovery date.

### 6.2 Recovery Amount

Constant recovery:

$$
\operatorname{RecoveryCash}_i = R_i F_{i,\tau_i}
$$

Stochastic recovery:

$$
R_i \sim \operatorname{Beta}(\alpha,\beta)
$$

with:

$$
E[R_i] = \frac{\alpha}{\alpha+\beta}
$$

Given mean $m$ and concentration $\kappa$:

$$
\alpha=m\kappa,\qquad \beta=(1-m)\kappa
$$

Optional factor-linked recovery:

$$
R_i = \operatorname{clip}(R_i^0 + \gamma M, R_{min}, R_{max})
$$

where $\gamma<0$ means recoveries are lower in bad systemic states.

### 6.3 Defaulted Asset Treatment

Defaulted assets must track:

```text
defaulted_par
market_value
expected_recovery
recovery_date
workout_sale_date
workout_interest
par haircut
eligibility status
proceeds bucket
```

Defaulted assets usually stop paying regular interest. Any recoveries, sale
proceeds, or workout proceeds must be classified according to the deal's
definitions of interest proceeds and principal proceeds.

## 7. Collateral Cash-Flow Engine

For each asset and collateral projection period, the engine computes:

```text
beginning par
fundings / delayed-draw advances
scheduled amortization
prepayments / repayments
sales
purchases
defaults
recoveries
ending par
performing par
defaulted par
interest proceeds
principal proceeds
trading gain/loss
```

### 7.1 Performing Interest

$$
Interest_{i,m}
= PerformingBalance_{i,m-1} \cdot c_{i,m}\cdot \Delta_{i,m}
$$

If interest is paid with a delay or settlement lag:

$$
ReceiptDate_{i,m}=AccrualEndDate_m+\operatorname{SettlementLag}_i
$$

### 7.2 Scheduled Principal

For amortizing assets:

$$
ScheduledPrincipal_{i,m}
= \min(ScheduleAmount_{i,m}, UPB_{i,m-1})
$$

For bullet assets:

$$
ScheduledPrincipal_{i,m}
= \mathbf{1}_{\{maturity_i \in m\}}UPB_{i,m-1}
$$

### 7.3 Prepayments and Repayments

For a conditional prepayment rate $CPR_m$:

$$
SMM_m = 1-(1-CPR_m)^{1/12}
$$

Monthly prepayment is:

$$
Prepay_{i,m}
= (UPB_{i,m-1}-ScheduledPrincipal_{i,m})SMM_m
$$

Loan-specific repayment dates override vector assumptions.

### 7.4 Sales

If an asset is sold:

$$
SaleProceeds_{i,m}=SoldPar_{i,m}\cdot S_{i,m}
$$

Trading gain/loss relative to par is:

$$
TradingPnL_{i,m}=SaleProceeds_{i,m}-SoldPar_{i,m}
$$

The model must preserve both cash proceeds and par impact, because OC tests may
use adjusted par while valuation uses market value.

### 7.5 Purchases and Reinvestment Assets

If principal proceeds are reinvested at purchase price $P_{new,m}$:

$$
PurchasedPar_m =
\frac{CashUsedForPurchases_m}{P_{new,m}}
$$

New assets inherit scenario-defined or sampled attributes:

```text
spread
floor
rating
rating factor
industry
country
maturity
recovery assumption
price
eligibility flags
default curve
prepayment vector
```

Purchases are subject to eligibility, concentration, quality, maturity, WAL, WAS,
WARF, CCC, cov-lite, fixed-rate, discount-obligation, and reinvestment OC tests.

### 7.6 Collateral Balance Roll-Forward

For each period:

$$
Par_{m}
= Par_{m-1}
+ Purchases_m
+ Fundings_m
- ScheduledPrincipal_m
- Prepayments_m
- SoldPar_m
- DefaultedPar_m
$$

This identity is a hard validation check.

## 8. Proceeds Accounts

The engine maintains explicit accounts:

```text
interest_proceeds
principal_proceeds
collection_account
payment_account
expense_reserve
interest_reserve
principal_reserve
supplemental_reserve
uninvested_cash
```

A transaction-specific mapping classifies each cash item:

| Cash item | Typical bucket |
|---|---|
| Performing loan interest | Interest proceeds |
| Commitment fees | Interest or other proceeds, deal-specific |
| Scheduled principal | Principal proceeds |
| Prepayments/repayments | Principal proceeds |
| Sale proceeds | Principal proceeds, with deal-specific gain treatment |
| Recoveries | Principal proceeds unless documents say otherwise |
| Workout interest | Interest or principal proceeds, deal-specific |
| Hedge receipts | Interest proceeds or hedge account |
| Reserve releases | Deal-specific |

Permitted transfers between accounts must be explicit. The model may not use
principal to pay interest, or interest to buy collateral, unless the deal terms
allow it.

## 9. Fees, Expenses, Taxes, and Hedges

The liability engine computes senior expenses, trustee/admin fees, collateral
manager fees, incentive fees, taxes, hedge payments, and reserve deposits.

Example management fee:

$$
MgmtFee_{q}^{senior}
= FeeRate^{senior}\cdot FeeBase_q\cdot \Delta_q
+ UnpaidSeniorMgmtFee_{q-1}
$$

Fee bases may be:

```text
aggregate collateral balance
performing collateral balance
adjusted collateral principal amount
original collateral balance
note balance
```

Caps, carryforward, subordination, incentive hurdles, and fee-waiver mechanics
must be line-item configuration, not hard-coded assumptions.

Hedge cash flows must support:

```text
fixed-floating swaps
basis swaps
caps/floors
termination payments
counterparty downgrade/reserve triggers
```

## 10. Liability and Note Balance Engine

For each tranche:

```text
beginning balance
interest due
interest paid
deferred interest
interest shortfall
principal paid
writedown
writeup
ending balance
controlling class status
timely interest flag
ultimate principal flag
```

The note balance roll-forward is:

$$
N_{j,q}
= N_{j,q-1}
- PrincipalPaid_{j,q}
- Writedown_{j,q}
+ Writeup_{j,q}
$$

No note balance may become negative. No principal payment may exceed outstanding
balance. Interest shortfall treatment is tranche-specific.

## 11. Collateral Quality and Concentration Tests

The institutional model computes collateral-quality tests before waterfalls and
before reinvestment eligibility decisions.

### 11.1 WARF

Given rating factor $RF_i$:

$$
WARF_q =
\frac{\sum_i EligiblePar_{i,q}RF_{i,q}}
     {\sum_i EligiblePar_{i,q}}
$$

The test passes if:

$$
WARF_q \le WARF_{max}
$$

### 11.2 Weighted-Average Spread

$$
WAS_q =
\frac{\sum_i EligiblePar_{i,q}s_i}
     {\sum_i EligiblePar_{i,q}}
$$

The test passes if:

$$
WAS_q \ge WAS_{min}
$$

### 11.3 Weighted-Average Life

For asset principal payments $Prin_{i,u}$ at future dates $u$:

$$
WAL^{asset}_q =
\frac{\sum_{i,u}(t_u-t_q)Prin_{i,u}}
     {\sum_{i,u}Prin_{i,u}}
$$

The test passes if:

$$
WAL^{asset}_q \le WAL_{max}(q)
$$

### 11.4 Diversity and Concentration

The model must support at least these concentration tests:

```text
largest obligor
top 5 obligors
industry
country
rating bucket
CCC/Caa excess
cov-lite
fixed-rate assets
second-lien assets
unsecured assets
discount obligations
long-dated assets
non-performing/defaulted assets
non-senior-secured assets
```

Test formulas are configured because deal documents differ. Results must report:

```text
test name
threshold
numerator
denominator
excess amount
pass/fail
impacted waterfall or reinvestment rule
```

## 12. Adjusted Collateral Principal Amount

OC tests usually use an adjusted collateral balance rather than raw par.

Generic form:

$$
ACPA_q =
PerformingPar_q
- Haircut^{defaulted}_q
- Haircut^{CCCExcess}_q
- Haircut^{discount}_q
- Haircut^{longdated}_q
- Haircut^{ineligible}_q
+ EligibleCash_q
$$

The engine must store each component separately.

Example defaulted asset haircut:

$$
Haircut^{defaulted}_{i,q}
= DefaultedPar_{i,q}
- \min(MV_{i,q}, RecoveryValue_{i,q}, Par_{i,q})
$$

Example discount obligation haircut:

$$
Haircut^{discount}_{i,q}
= \max(0, Par_{i,q}-PurchasePrice_{i,q}Par_{i,q})
$$

The actual formula is deal-specific and must be loaded from `TestConfig`.

## 13. OC and IC Coverage Tests

Coverage tests are class-specific. For a test class $k$, define the included note
set:

$$
\mathcal{J}_{\le k} = \{j: seniority_j \le seniority_k\}
$$

### 13.1 Overcollateralization

$$
OC_{k,q}
= \frac{ACPA_q}
       {\sum_{j\in\mathcal{J}_{\le k}}N_{j,q-1}}
$$

The test passes if:

$$
OC_{k,q} \ge OCTrigger_{k,q}
$$

If the denominator is zero because every included class has been paid in full,
the test status is `not_applicable_paid_off` unless the deal documents specify a
different residual test.

### 13.2 Interest Coverage

$$
IC_{k,q}
= \frac{InterestProceedsForTest_{k,q}}
       {\sum_{j\in\mathcal{J}_{\le k}}I^{due}_{j,q}}
$$

The test passes if:

$$
IC_{k,q} \ge ICTrigger_{k,q}
$$

If the denominator is zero because no included class has interest due, the test
status is `not_applicable_no_interest_due` unless the deal documents specify a
different treatment.

### 13.3 Reinvestment OC

Some deals apply a reinvestment OC or par-value test to determine whether
principal may be reinvested:

$$
ReinvOC_q =
\frac{ACPA_q + EligiblePrincipalCash_q}
     {TargetParOrRatedDebt_q}
$$

If the test fails, principal proceeds that otherwise would be reinvested are used
to pay down notes according to the principal waterfall.

## 14. Waterfall Engine

The model supports multiple waterfalls:

```text
interest proceeds waterfall
principal proceeds waterfall
post-reinvestment principal waterfall
coverage-test diversion waterfall
optional redemption waterfall
acceleration/enforcement waterfall
special proceeds/workout waterfall
hedge termination waterfall
```

Each waterfall is represented as ordered line items:

```text
line_id
source_account
target_account_or_payee
amount_due_formula
cap_formula
shortfall_rule
carryforward_rule
skip_condition
test_condition
balance_update
```

### 14.1 Generic Payment Operator

For line item $\ell$:

$$
Paid_{\ell,q}
= \min(Available_{\ell,q}, Due_{\ell,q}, Cap_{\ell,q})
$$

Shortfall:

$$
Shortfall_{\ell,q}
= Due_{\ell,q} - Paid_{\ell,q}
$$

Available cash after payment:

$$
Available_{\ell+1,q}
= Available_{\ell,q} - Paid_{\ell,q}
$$

Every line item must preserve a source/use audit record.

### 14.2 Interest Proceeds Waterfall

A typical configurable order:

```text
1. taxes and senior expenses
2. trustee/admin/capped expenses
3. hedge payments senior in the waterfall
4. senior management fee
5. Class A interest
6. Class B interest
7. Class C interest
8. Class D interest
9. Class E/F interest, including deferrable treatment
10. coverage-test diversion to principal paydown if applicable
11. subordinated management fee
12. deferred interest and interest-on-interest, if applicable
13. incentive management fee
14. reserve deposits or releases
15. residual to subordinated notes/equity
```

The exact order is deal-specific.

### 14.3 Principal Proceeds Waterfall

During the reinvestment period:

```text
1. purchase eligible collateral if reinvestment is allowed
2. cure coverage-test failures if required
3. pay required principal on notes if reinvestment is not allowed
4. deposit to principal or ramp-up accounts if required
5. residual principal treatment, if any
```

After the reinvestment period:

```text
1. pay Class A principal until zero
2. pay Class B principal until zero
3. pay Class C principal until zero
4. pay Class D principal until zero
5. pay Class E/F principal until zero
6. residual principal to subordinated notes/equity if permitted
```

Sequential, pro rata, modified pro rata, turbo, target amortization, and
controlling-class paydown rules must be supported as configurable modes.

### 14.4 Coverage-Test Diversion

If any applicable OC/IC test fails, the model identifies the controlling failed
test and the amount otherwise payable to junior notes, fees, or equity that must
be redirected:

$$
Diversion_q =
\min(AvailableAfterProtectedLines_q,\ RequiredCureAmount_q)
$$

If documents say "divert all remaining proceeds until cured":

$$
Diversion_q = AvailableAfterProtectedLines_q
$$

Principal paydown from diverted interest follows the configured cure waterfall.

### 14.5 Cure Amount

A generic OC cure amount for class $k$ is the senior debt reduction $x$ needed
to restore the ratio:

$$
\frac{ACPA_q}{Debt_{\le k,q}-x} \ge OCTrigger_{k,q}
$$

so:

$$
x \ge Debt_{\le k,q} - \frac{ACPA_q}{OCTrigger_{k,q}}
$$

The implemented cure amount is:

$$
CureAmount_{k,q}
= \max\left(0,\ Debt_{\le k,q} - \frac{ACPA_q}{OCTrigger_{k,q}}\right)
$$

bounded by outstanding debt and available divertible cash. Deal documents may
instead require all remaining interest to be paid as principal regardless of this
calculated amount.

## 15. Reinvestment and Trading Rules

Reinvestment is allowed only if:

```text
current date is within reinvestment period
no event of default or acceleration blocks reinvestment
coverage tests satisfy required levels or cure provisions
reinvestment OC/par tests pass
collateral-quality tests pass before and after purchase
concentration tests pass or purchases improve compliance
asset eligibility criteria are met
manager trading limits are not exceeded
```

If reinvestment is blocked, eligible principal proceeds follow the principal
waterfall.

The model must support:

```text
ramp-up purchases
scheduled reinvestment
unscheduled reinvestment
credit risk sales
credit improved sales
discretionary sales
substitution
reinvestment at premium or discount
par build and par erosion
```

Each trade must produce:

```text
cash impact
par impact
gain/loss versus par
market-value impact
test impact
eligibility impact
```

## 16. Valuation

### 16.1 Scenario Present Value

For tranche $j$ and scenario $s$:

$$
PV_{j,s}
= \sum_q CF_{j,q,s}DF_j(t_q)
$$

Expected value:

$$
Value_j = \frac{1}{S}\sum_{s=1}^{S}PV_{j,s}
$$

### 16.2 Discount Curves

The model supports:

```text
risk-free curve
benchmark forward curve
discount-margin curve
OAS curve
tranche-specific required yield
market price implied yield
```

Flat discounting is allowed only as an explicit simplified mode:

$$
DF_j(t_q)=e^{-d_jt_q}
$$

or:

$$
DF_j(t_q)=\frac{1}{(1+d_j\Delta_q)^q}
$$

### 16.3 Price, Yield, DM, and OAS

Given a clean price $Price_j$, solve yield $y_j$:

$$
Price_j + Accrued_j =
\sum_q \frac{ExpectedCF_{j,q}}{(1+y_j\Delta_q)^{n_q}}
$$

Discount margin $DM_j$ solves:

$$
Price_j + Accrued_j =
\sum_q ExpectedCF_{j,q} \cdot DF^{benchmark+DM_j}(t_q)
$$

OAS solves the analogous spread over the risk-neutral or scenario-adjusted curve.
All reported valuation outputs must state whether cash flows are deterministic,
expected under Monte Carlo, rating-stress cash flows, or trustee-report actuals.

## 17. Tranche Metrics

For $S$ scenarios and tranche $j$:

$$
EL_j =
\frac{1}{S}\sum_{s=1}^{S}\frac{Loss_{j,s}}{N_{j,0}}
$$

Probability of principal loss:

$$
PPL_j =
\frac{1}{S}\sum_{s=1}^{S}\mathbf{1}_{\{Loss_{j,s}>0\}}
$$

Probability of interest shortfall:

$$
PIS_j =
\frac{1}{S}\sum_{s=1}^{S}\mathbf{1}_{\{\exists q: Shortfall_{j,q,s}>0\}}
$$

Probability of impairment:

$$
PI_j =
\frac{1}{S}\sum_{s=1}^{S}
\mathbf{1}_{\{PrincipalPaid_{j,s}+EndingBalance_{j,s}<N_{j,0}\}}
$$

Weighted-average life:

$$
WAL_j =
\frac{\sum_q t_q \cdot PrincipalPaid_{j,q}}
     {\sum_q PrincipalPaid_{j,q}}
$$

If principal is not fully repaid in some scenarios, report WAL conditional on
full repayment and separately report impairment frequency.

## 18. Equity Metrics

Let $E_0$ be equity purchase price or retained equity investment. Expected equity
cash flow is:

$$
ECF_q = \frac{1}{S}\sum_{s=1}^{S}CF_{equity,q,s}
$$

Net total return:

$$
NetReturn =
\frac{\sum_q ECF_q - E_0}{E_0}
$$

Multiple on invested capital:

$$
MOIC =
\frac{\sum_q ECF_q}{E_0}
$$

IRR solves:

$$
0 = -E_0 + \sum_q \frac{ECF_q}{(1+IRR)^{t_q}}
$$

If cash flows have multiple sign changes, report NPV and MIRR in addition to, or
instead of, IRR.

## 19. Rating and Stress Analysis Modes

The engine has four non-proprietary modes.

### 19.1 Academic Rating Mode

Solve for the largest Class A notional such that expected loss is below the
assigned academic threshold:

$$
EL_A(N_A) \le \theta_{Aa}
$$

Use common random numbers across the bisection grid to reduce simulation noise.

### 19.2 Deterministic Rating-Style Stress Mode

Run specified combinations of:

```text
default rate vector
default timing vector
recovery rate
recovery lag
interest-rate path
spread path
prepayment path
reinvestment price/spread/rating
manager trading behavior
expense stress
haircut assumptions
```

Outputs are pass/fail and cash-flow sufficiency diagnostics, not agency ratings.

### 19.3 Monte Carlo Risk Mode

Use stochastic default, recovery, prepayment, spread, and rate scenarios to
estimate distributions of:

```text
tranche loss
interest shortfall
PV
yield
WAL
coverage-test breaches
equity IRR
```

### 19.4 Break-Even Mode

Solve for the stress level at which a target tranche first fails a criterion:

```text
break-even CDR
break-even cumulative default rate
break-even recovery
break-even spread compression
break-even prepayment speed
break-even reinvestment price
```

The criterion can be no principal loss, timely interest, ultimate interest, a
target EL, or a minimum value/yield.

## 20. Monte Carlo Error and Reproducibility

Every simulation result must include:

```text
seed
random number generator
n_scenarios
scenario mode
mean
sample standard deviation
standard error
confidence interval
number of tail observations
convergence diagnostics
```

For independent scenarios:

$$
SE(\bar{X})=\frac{sample\_std(X)}{\sqrt{S}}
$$

The engine must warn when senior-tranche tail metrics rely on too few loss
observations. Required convergence grid:

$$
S \in \{1{,}000,\ 5{,}000,\ 10{,}000,\ 50{,}000,\ 100{,}000\}
$$

## 21. Validation Identities

### 21.1 Credit Model

Latent correlation:

$$
\operatorname{Corr}(Y_i,Y_k)\to\rho
$$

Marginal default frequency:

$$
\frac{1}{S}\sum_s\mathbf{1}_{\{\tau_{i,s}\le t\}}\to Q_i(t)
$$

Joint default probability for equal threshold $c=\Phi^{-1}(Q(t))$:

$$
P(default_i,default_k)=\Phi_2(c,c;\rho)
$$

Default-event correlation:

$$
\operatorname{Corr}(\mathbf{1}_i,\mathbf{1}_k)
=
\frac{\Phi_2(c,c;\rho)-Q(t)^2}{Q(t)(1-Q(t))}
$$

This is not equal to latent correlation except in special cases.

### 21.2 Collateral Roll-Forward

$$
BeginningPar + Purchases + Fundings
- ScheduledPrincipal - Prepayments - Sales - Defaults
= EndingPar
$$

### 21.3 Liability Roll-Forward

$$
BeginningNoteBalance - PrincipalPaid - Writedown + Writeup
= EndingNoteBalance
$$

### 21.4 Cash Source/Use

For each proceeds account:

$$
BeginningCash + Sources - Uses = EndingCash
$$

No waterfall line may make available cash negative unless the deal explicitly
permits overdraft or liquidity draws and those draws are modeled.

### 21.5 Edge Cases

The engine must pass:

```text
Q(t)=0 -> no defaults
Q(t)=1 and R=0 -> deterministic full collateral loss
rho=0 -> independent defaults
single-name portfolio -> exact Bernoulli loss distribution
LGD=0 -> no principal losses
zero note coupon -> no interest due
no collateral principal -> no principal paydown
all notes paid -> residual principal follows deal terms
failed OC test -> configured diversion occurs before residual equity
reinvestment disabled -> principal pays down notes after required uses
```

## 22. Required Output Tables

The engine returns typed results equivalent to these tables.

### 22.1 Asset Period Cash Flows

```text
scenario | period | asset_id | beginning_par | interest | scheduled_principal
prepayment | sale_par | sale_proceeds | defaulted_par | recovery | purchase_par
ending_par | performing_par | defaulted_par_outstanding | proceeds_bucket
```

### 22.2 Coverage Tests

```text
scenario | payment_date | test_name | class | numerator | denominator
threshold | ratio | excess_or_shortfall | pass_fail | cure_amount
```

### 22.3 Waterfall Trace

```text
scenario | payment_date | waterfall | line_id | line_name | source_account
amount_due | amount_paid | shortfall | carryforward | available_after
balance_update | trigger_reference
```

### 22.4 Tranche Cash Flows

```text
scenario | payment_date | tranche | beginning_balance | interest_due
interest_paid | deferred_interest | principal_paid | writedown | writeup
ending_balance | cash_flow_to_investor
```

### 22.5 Valuation and Risk Metrics

```text
scenario_set | tranche | price | value | yield | discount_margin | OAS
EL | PPL | PIS | PI | WAL | duration | IRR | standard_error
confidence_interval | n_scenarios | seed
```

## 23. Implementation Boundary

The engine computes:

```text
default times and deterministic default vectors
recoveries and recovery lags
asset-level collateral cash flows
proceeds account classification
fees, expenses, hedges, and reserves
coverage and collateral-quality tests
interest and principal waterfalls
reinvestment and trading eligibility
tranche cash flows, losses, balances, and shortfalls
valuation, yield, DM/OAS, WAL, IRR, and risk metrics
validation reconciliations
```

The agent may:

```text
parse deal terms
fetch and normalize collateral tapes
fetch curves, prices, ratings, and default tables
select scenario sets
call deterministic solvers
run stress and break-even workflows
write reports and explain outputs
```

The agent must not:

```text
sample defaults
apply waterfalls
calculate tranche losses
discount cash flows
classify proceeds without the configured mapping
assign numeric ratings directly
override failed validations
```

All reported numbers must be traceable to typed engine results, input data
versions, scenario definitions, market-data timestamps, and model version.
