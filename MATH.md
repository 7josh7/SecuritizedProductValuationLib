# SecuritizedProductValuationLib Math Specification

This file is the quantitative contract for the first product module: a cash CDO/CLO valuation engine. The implementation should be deterministic given its inputs and random seed. The agent layer may select inputs, run scenarios, and explain results, but it must not perform valuation arithmetic.

## 1. Notation

| Symbol | Meaning |
|---|---|
| `i` | Obligor or collateral bond index |
| `j` | Tranche index |
| `q` | Payment period index, usually quarterly |
| `t` | Time in years |
| `T` | Deal horizon or maturity |
| `F_i` | Face value of collateral bond `i` |
| `c_i` | Annual coupon rate of collateral bond `i` |
| `N_j` | Tranche notional for tranche `j` |
| `r_j` | Annual coupon/spread rate for tranche `j` |
| `Q_i(t)` | Cumulative default probability for name `i` by time `t` |
| `lambda_i(t)` | Hazard rate for name `i` |
| `R_i` | Recovery rate on name `i` |
| `LGD_i` | Loss given default, `1 - R_i` |
| `tau_i` | Default time of name `i` |
| `rho` | Pairwise latent asset correlation |
| `a` | One-factor loading, where `rho = a^2` |
| `M` | Common systematic factor |
| `Z_i` | Idiosyncratic factor for name `i` |
| `Y_i` | Latent asset variable for name `i` |

The baseline academic setup uses a 5-year horizon, 20 quarterly periods, flat annual default probability, constant LGD, and a simple senior/mezzanine/equity waterfall. The industry-grade setup generalizes those assumptions.

## 2. Time Grid and Cash-Flow Dates

For a quarterly structure with maturity `T = 5`, define:

```text
Delta = 0.25
t_q = q * Delta, q = 1, 2, ..., 20
```

Coupon cash flows are paid at each `t_q`. Principal is repaid at maturity unless a bond has defaulted before maturity. A bond that defaults in period `q` stops paying future coupons and contributes a recovery cash flow according to the configured recovery timing convention.

The default recovery convention proposed for v1 is:

```text
recovery_period(tau_i) = min q such that t_{q-1} < tau_i <= t_q
```

Recovery cash is recognized in that period.

## 3. One-Factor Gaussian Copula

Each obligor has a latent asset variable:

```text
Y_i = a * M + sqrt(1 - a^2) * Z_i
```

with:

```text
M ~ N(0, 1)
Z_i ~ N(0, 1)
M independent of all Z_i
Z_i independent across obligors
```

The latent asset correlation between any two names is:

```text
Corr(Y_i, Y_k) = a^2 = rho
```

Therefore, if the target latent asset correlation is `rho`, the factor loading is:

```text
a = sqrt(rho)
```

For the academic correlation of `rho = 0.20`:

```text
a = sqrt(0.20) = 0.4472135955
```

## 4. Mapping Latent Variables to Default

Let `Phi` be the standard normal CDF. Define:

```text
U_i = Phi(Y_i)
```

Then `U_i` is uniform on `[0, 1]`. Name `i` defaults by time `t` if:

```text
U_i <= Q_i(t)
```

Equivalently:

```text
Y_i <= Phi^{-1}(Q_i(t))
```

This preserves the desired marginal default probability:

```text
P(default by t) = P(U_i <= Q_i(t)) = Q_i(t)
```

## 5. Default-Time Sampling

Default times are needed because the cash waterfall is quarterly. Given `U_i`, default time is the inverse cumulative default curve:

```text
tau_i = Q_i^{-1}(U_i)
```

For a constant hazard rate `lambda_i`:

```text
Q_i(t) = 1 - exp(-lambda_i * t)
```

Solving for `t` gives:

```text
tau_i = -ln(1 - U_i) / lambda_i
```

This is the correct orientation. Low latent credit quality gives low `U_i`, which gives early default. The formula `-ln(U_i) / lambda_i` would reverse the ordering and is incorrect for this construction.

Default within horizon `T` occurs when:

```text
tau_i <= T
```

which is equivalent to:

```text
U_i <= Q_i(T)
```

## 6. Default Curves and Hazard Rates

### 6.1 Constant Hazard

If a cumulative default probability `Q(T)` is supplied for horizon `T`, the flat hazard rate is:

```text
lambda = -ln(1 - Q(T)) / T
```

Then the cumulative curve at any time `t` is:

```text
Q(t) = 1 - exp(-lambda * t)
```

### 6.2 Piecewise-Constant Hazard

For a default table with cumulative probabilities at tenors:

```text
0 = T_0 < T_1 < ... < T_K
Q(T_k)
```

the survival probability is:

```text
S(T_k) = 1 - Q(T_k)
```

The piecewise hazard on interval `(T_{k-1}, T_k]` is:

```text
lambda_k = -ln(S(T_k) / S(T_{k-1})) / (T_k - T_{k-1})
```

For `t` in `(T_{k-1}, T_k]`:

```text
S(t) = S(T_{k-1}) * exp(-lambda_k * (t - T_{k-1}))
Q(t) = 1 - S(t)
```

To invert the curve, find the first interval where:

```text
Q(T_{k-1}) < U_i <= Q(T_k)
```

then:

```text
tau_i = T_{k-1} - ln((1 - U_i) / S(T_{k-1})) / lambda_k
```

If `U_i > Q(T_K)`, the name survives beyond the last curve tenor.

## 7. Recovery and Loss Given Default

### 7.1 Constant Recovery

The academic baseline uses constant LGD:

```text
LGD_i = 60%
R_i = 40%
loss_i = LGD_i * F_i
recovery_cash_i = R_i * F_i
```

### 7.2 Stochastic Recovery

The industry option models recovery as beta-distributed:

```text
R_i ~ Beta(alpha, beta)
```

with:

```text
E[R_i] = alpha / (alpha + beta)
Var[R_i] = alpha * beta / ((alpha + beta)^2 * (alpha + beta + 1))
```

Given target mean `m` and concentration `kappa`:

```text
alpha = m * kappa
beta = (1 - m) * kappa
```

Then:

```text
LGD_i = 1 - R_i
loss_i = LGD_i * F_i
```

Recovery draws should be seeded and reproducible. A later extension may correlate recovery with the systemic factor `M`, but v1 may keep recovery independent.

## 8. Collateral Cash Flows

For each period `q`, the collateral coupon from name `i` is:

```text
coupon_{i,q} = alive_{i,q} * c_i * F_i * Delta
```

where `alive_{i,q}` is 1 if name `i` has not defaulted before the coupon accrual cutoff and 0 otherwise.

Recovery cash in period `q` is:

```text
recovery_{i,q} = 1_{tau_i in period q} * R_i * F_i
```

Principal at maturity is:

```text
principal_{i,q} = 1_{q = final} * 1_{tau_i > T} * F_i
```

Total collateral cash available in period `q` is:

```text
C_q = sum_i coupon_{i,q} + sum_i recovery_{i,q} + sum_i principal_{i,q}
```

Collateral par outstanding after defaults is:

```text
Par_q = sum_i 1_{tau_i > t_q} * F_i
```

Collateral interest for coverage tests is usually:

```text
Interest_q = sum_i 1_{tau_i > t_{q-1}} * c_i * F_i * Delta
```

The exact timing convention must be declared in `DealConfig`.

## 9. Simple Waterfall

The academic baseline waterfall pays:

1. Class A interest
2. Class B interest
3. Residual to equity

For tranche `j`, interest due in period `q` is:

```text
I_{j,q} = r_j * N_{j,q-1} * Delta + carried_shortfall_{j,q-1}
```

Payment is:

```text
P_{j,q}^{interest} = min(available_cash, I_{j,q})
```

Unpaid interest shortfall is:

```text
shortfall_{j,q} = I_{j,q} - P_{j,q}^{interest}
```

Remaining cash after debt interest goes to equity:

```text
Equity_q = max(available_cash_after_debt_interest, 0)
```

In the academic baseline, tranche principal repayment and loss allocation are measured through end-of-horizon collateral losses. In the industry cash-flow version, principal paydowns and writedowns are tracked directly through the waterfall.

## 10. OC and IC Tests

### 10.1 Overcollateralization Test

For senior tranche A:

```text
OC_q = collateral_par_q / senior_notional_outstanding_q
```

The test passes if:

```text
OC_q >= OC_trigger
```

If the test fails, residual cash that would otherwise go to mezzanine/equity may be diverted to pay down senior principal until the test is cured or cash is exhausted.

### 10.2 Interest Coverage Test

```text
IC_q = collateral_interest_q / senior_interest_due_q
```

The test passes if:

```text
IC_q >= IC_trigger
```

If the test fails, available residual cash is diverted to senior deleveraging, subject to the deal's priority of payments.

### 10.3 Diversion Amount

A simple v1 diversion rule is:

```text
diversion_q = available_cash_after_senior_interest
```

when either OC or IC fails. Senior principal paydown is:

```text
paydown_{A,q} = min(diversion_q, N_{A,q-1})
N_{A,q} = N_{A,q-1} - paydown_{A,q}
```

Real deal documents can define different cure mechanics. The chosen convention must be explicit.

## 11. Tranche Loss Allocation

Let total portfolio loss at horizon be:

```text
L = sum_i 1_{tau_i <= T} * LGD_i * F_i
```

For an attachment point `A_j` and detachment point `D_j`, tranche loss is:

```text
TL_j = min(max(L - A_j, 0), D_j - A_j)
```

As a percentage of tranche notional:

```text
tl_j = TL_j / (D_j - A_j)
```

For named tranche notionals in the academic structure, losses are allocated in reverse seniority:

```text
equity absorbs first
then Class B
then Class A
```

If the capital structure has:

```text
N_E = equity notional
N_B = Class B notional
N_A = Class A notional
```

then:

```text
Loss_E = min(L, N_E)
Loss_B = min(max(L - N_E, 0), N_B)
Loss_A = min(max(L - N_E - N_B, 0), N_A)
```

## 12. Tranche Metrics

For `S` Monte Carlo scenarios and tranche `j`, define scenario loss `Loss_{j,s}`.

Expected loss is:

```text
EL_j = (1 / S) * sum_s Loss_{j,s} / N_j
```

Probability of any principal loss is:

```text
PD_j = (1 / S) * sum_s 1_{Loss_{j,s} > 0}
```

Mean loss amount is:

```text
MeanLoss_j = (1 / S) * sum_s Loss_{j,s}
```

Loss standard error is:

```text
SE(MeanLoss_j) = sample_std(Loss_{j,s}) / sqrt(S)
```

For expected loss percentage:

```text
SE(EL_j) = SE(MeanLoss_j) / N_j
```

A normal-approximate 95% confidence interval is:

```text
EL_j +/- 1.96 * SE(EL_j)
```

For low-probability senior losses, the engine should report the number of loss scenarios and warn when tail estimates are based on very few observations.

## 13. Valuation

For tranche `j`, scenario cash flows are `CF_{j,q,s}`. Discount factor for period `q` is `DF_j(t_q)`.

Scenario present value:

```text
PV_{j,s} = sum_q CF_{j,q,s} * DF_j(t_q)
```

Tranche value:

```text
Value_j = (1 / S) * sum_s PV_{j,s}
```

If using a flat discount rate `d_j`:

```text
DF_j(t_q) = exp(-d_j * t_q)
```

or, with periodic compounding:

```text
DF_j(t_q) = 1 / (1 + d_j * Delta)^q
```

The convention must be explicit. The design target is:

```text
Class A discount rate = risk-free + 50 bp
Class B discount rate = Treasury rate + 400 bp
Equity value = discounted residual cash flows, plus IRR
```

## 14. Equity ROE and IRR

Let the retained equity investment be `E_0`. Let expected equity cash flow at period `q` be:

```text
ECF_q = (1 / S) * sum_s CF_{equity,q,s}
```

Simple total return is:

```text
TotalReturn = (sum_q ECF_q - E_0) / E_0
```

ROE may be reported as:

```text
ROE = sum_q ECF_q / E_0
```

or as net return:

```text
NetROE = (sum_q ECF_q - E_0) / E_0
```

The report must label which one is used.

IRR solves:

```text
0 = -E_0 + sum_q ECF_q / (1 + IRR)^{t_q}
```

If cash flows have multiple sign changes, IRR may be unstable; in that case report NPV at a chosen discount rate as the primary measure.

## 15. Academic Rating Mode

The academic rating mode solves for the largest Class A notional such that expected loss remains below the assigned threshold.

Let the threshold for Aa be:

```text
theta_Aa
```

The condition is:

```text
EL_A(N_A) <= theta_Aa
```

The solver searches over `N_A`:

```text
low = 0
high = collateral_notional
while high - low > tolerance:
    mid = (low + high) / 2
    run simulation with N_A = mid
    if EL_A(mid) <= theta_Aa:
        low = mid
    else:
        high = mid
```

The result is:

```text
N_A^* = low
```

Because simulation noise can move the boundary, the production solver should either use common random numbers across bisection steps or use a sufficiently large scenario count with confidence intervals.

## 16. Agency-Style Approximation

The agency-style mode does not claim to reproduce proprietary Moody's or S&P criteria. It reports a transparent set of diagnostics:

```text
expected loss
probability of impairment
probability of principal loss
weighted-average life
stress expected loss
stress probability of loss
coverage-test breach frequency
interest shortfall frequency
```

Weighted-average life for tranche `j` is:

```text
WAL_j = sum_q t_q * principal_payment_{j,q} / sum_q principal_payment_{j,q}
```

If principal is not fully repaid in some scenarios, report WAL conditional on repayment and separately report impairment frequency.

## 17. Monte Carlo Standard Error and Reproducibility

Every simulation result must include:

```text
seed
n_scenarios
mean
standard_error
confidence_interval
```

For independent scenarios:

```text
SE(mean X) = sample_std(X) / sqrt(S)
```

Convergence should be checked by running increasing scenario counts:

```text
S = 1,000; 5,000; 10,000; 50,000
```

Standard errors should shrink approximately as:

```text
SE_S proportional to 1 / sqrt(S)
```

## 18. Validation Identities

### 18.1 Latent Correlation

Across simulated scenarios:

```text
Corr(Y_i, Y_k) -> rho
```

This validates the Gaussian copula construction.

### 18.2 Marginal Default Frequency

For each name and horizon:

```text
(1 / S) * sum_s 1_{tau_{i,s} <= t} -> Q_i(t)
```

### 18.3 Joint Default Probability

For two names with identical default threshold `c = Phi^{-1}(Q(t))`:

```text
P(default_i, default_k) = Phi_2(c, c; rho)
```

where `Phi_2` is the bivariate normal CDF with correlation `rho`.

The default-event correlation is:

```text
Corr(1_i, 1_k) = (Phi_2(c, c; rho) - Q(t)^2) / (Q(t) * (1 - Q(t)))
```

This is not equal to latent correlation `rho` except in special cases.

### 18.4 Edge Cases

The engine must pass:

```text
Q(t) = 0        -> no defaults
Q(t) = 1, R = 0 -> full deterministic collateral loss
rho = 0        -> independent defaults
single name    -> exact Bernoulli loss distribution
LGD = 0        -> no principal losses
```

## 19. Implementation Boundary

The engine computes:

```text
default times
recoveries
collateral cash flows
waterfall traces
tranche metrics
valuation
rating diagnostics
```

The agent may:

```text
parse deal terms
fetch default-rate tables
select the correct horizon
call deterministic solvers
run stress scenarios
write reports
explain outputs
```

The agent must not:

```text
sample defaults
apply the waterfall
calculate tranche losses
discount cash flows
assign numeric ratings directly
```

All reported numbers must be traceable to typed engine results.
