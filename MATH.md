# SecuritizedProductValuationLib Math Specification

This file is the quantitative contract for the first product module: a cash CDO/CLO valuation engine. The implementation should be deterministic given its inputs and random seed. The agent layer may select inputs, run scenarios, and explain results, but it must not perform valuation arithmetic.

GitHub renders the formulas in this document as LaTeX math.

## 1. Notation

| Symbol | Meaning |
|---|---|
| $i$ | Obligor or collateral bond index |
| $j$ | Tranche index |
| $q$ | Payment period index, usually quarterly |
| $t$ | Time in years |
| $T$ | Deal horizon or maturity |
| $F_i$ | Face value of collateral bond $i$ |
| $c_i$ | Annual coupon rate of collateral bond $i$ |
| $N_j$ | Tranche notional for tranche $j$ |
| $r_j$ | Annual coupon/spread rate for tranche $j$ |
| $Q_i(t)$ | Cumulative default probability for name $i$ by time $t$ |
| $\lambda_i(t)$ | Hazard rate for name $i$ |
| $R_i$ | Recovery rate on name $i$ |
| $\mathrm{LGD}_i$ | Loss given default, $1 - R_i$ |
| $\tau_i$ | Default time of name $i$ |
| $\rho$ | Pairwise latent asset correlation |
| $a$ | One-factor loading, where $\rho = a^2$ |
| $M$ | Common systematic factor |
| $Z_i$ | Idiosyncratic factor for name $i$ |
| $Y_i$ | Latent asset variable for name $i$ |

The baseline academic setup uses a 5-year horizon, 20 quarterly periods, flat annual default probability, constant LGD, and a simple senior/mezzanine/equity waterfall. The industry-grade setup generalizes those assumptions.

## 2. Time Grid and Cash-Flow Dates

For a quarterly structure with maturity $T = 5$, define:

$$
\Delta = 0.25
$$

$$
t_q = q\Delta,\qquad q = 1,2,\ldots,20
$$

Coupon cash flows are paid at each $t_q$. Principal is repaid at maturity unless a bond has defaulted before maturity. A bond that defaults in period $q$ stops paying future coupons and contributes a recovery cash flow according to the configured recovery timing convention.

The default recovery convention proposed for v1 is:

$$
\operatorname{recovery\_period}(\tau_i)
= \min \{q : t_{q-1} < \tau_i \le t_q\}
$$

Recovery cash is recognized in that period.

## 3. One-Factor Gaussian Copula

Each obligor has a latent asset variable:

$$
Y_i = aM + \sqrt{1-a^2}\,Z_i
$$

with:

$$
M \sim \mathcal{N}(0,1)
$$

$$
Z_i \sim \mathcal{N}(0,1)
$$

$$
M \perp Z_i,\qquad Z_i \perp Z_k \text{ for } i \ne k
$$

The latent asset correlation between any two names is:

$$
\operatorname{Corr}(Y_i,Y_k) = a^2 = \rho
$$

Therefore, if the target latent asset correlation is $\rho$, the factor loading is:

$$
a = \sqrt{\rho}
$$

For the academic correlation of $\rho = 0.20$:

$$
a = \sqrt{0.20} \approx 0.4472135955
$$

## 4. Mapping Latent Variables to Default

Let $\Phi$ be the standard normal CDF. Define:

$$
U_i = \Phi(Y_i)
$$

Then $U_i$ is uniform on $[0,1]$. Name $i$ defaults by time $t$ if:

$$
U_i \le Q_i(t)
$$

Equivalently:

$$
Y_i \le \Phi^{-1}\left(Q_i(t)\right)
$$

This preserves the desired marginal default probability:

$$
\mathbb{P}(\text{default by } t)
= \mathbb{P}\left(U_i \le Q_i(t)\right)
= Q_i(t)
$$

## 5. Default-Time Sampling

Default times are needed because the cash waterfall is quarterly. Given $U_i$, default time is the inverse cumulative default curve:

$$
\tau_i = Q_i^{-1}(U_i)
$$

For a constant hazard rate $\lambda_i$:

$$
Q_i(t) = 1 - e^{-\lambda_i t}
$$

Solving for $t$ gives:

$$
\tau_i = \frac{-\ln(1-U_i)}{\lambda_i}
$$

This is the correct orientation. Low latent credit quality gives low $U_i$, which gives early default. The formula $-\ln(U_i)/\lambda_i$ would reverse the ordering and is incorrect for this construction.

Default within horizon $T$ occurs when:

$$
\tau_i \le T
$$

which is equivalent to:

$$
U_i \le Q_i(T)
$$

## 6. Default Curves and Hazard Rates

### 6.1 Constant Hazard

If a cumulative default probability $Q(T)$ is supplied for horizon $T$, the flat hazard rate is:

$$
\lambda = \frac{-\ln\left(1-Q(T)\right)}{T}
$$

Then the cumulative curve at any time $t$ is:

$$
Q(t) = 1 - e^{-\lambda t}
$$

### 6.2 Piecewise-Constant Hazard

For a default table with cumulative probabilities at tenors:

$$
0 = T_0 < T_1 < \cdots < T_K
$$

with cumulative default probabilities $Q(T_k)$, the survival probability is:

$$
S(T_k) = 1 - Q(T_k)
$$

The piecewise hazard on interval $(T_{k-1}, T_k]$ is:

$$
\lambda_k =
\frac{-\ln\left(S(T_k) / S(T_{k-1})\right)}
{T_k - T_{k-1}}
$$

For $t \in (T_{k-1},T_k]$:

$$
S(t) = S(T_{k-1})e^{-\lambda_k(t-T_{k-1})}
$$

$$
Q(t) = 1 - S(t)
$$

To invert the curve, find the first interval where:

$$
Q(T_{k-1}) < U_i \le Q(T_k)
$$

then:

$$
\tau_i =
T_{k-1}
- \frac{\ln\left((1-U_i)/S(T_{k-1})\right)}{\lambda_k}
$$

If $U_i > Q(T_K)$, the name survives beyond the last curve tenor.

## 7. Recovery and Loss Given Default

### 7.1 Constant Recovery

The academic baseline uses constant LGD:

$$
\mathrm{LGD}_i = 60\%
$$

$$
R_i = 40\%
$$

$$
\mathrm{loss}_i = \mathrm{LGD}_i F_i
$$

$$
\mathrm{recovery\_cash}_i = R_i F_i
$$

### 7.2 Stochastic Recovery

The industry option models recovery as beta-distributed:

$$
R_i \sim \operatorname{Beta}(\alpha,\beta)
$$

with:

$$
\mathbb{E}[R_i] = \frac{\alpha}{\alpha+\beta}
$$

$$
\operatorname{Var}(R_i)
= \frac{\alpha\beta}{(\alpha+\beta)^2(\alpha+\beta+1)}
$$

Given target mean $m$ and concentration $\kappa$:

$$
\alpha = m\kappa
$$

$$
\beta = (1-m)\kappa
$$

Then:

$$
\mathrm{LGD}_i = 1 - R_i
$$

$$
\mathrm{loss}_i = \mathrm{LGD}_i F_i
$$

Recovery draws should be seeded and reproducible. A later extension may correlate recovery with the systemic factor $M$, but v1 may keep recovery independent.

## 8. Collateral Cash Flows

For each period $q$, the collateral coupon from name $i$ is:

$$
\operatorname{coupon}_{i,q}
= \operatorname{alive}_{i,q} c_i F_i \Delta
$$

where $\operatorname{alive}_{i,q}$ is 1 if name $i$ has not defaulted before the coupon accrual cutoff and 0 otherwise.

Recovery cash in period $q$ is:

$$
\operatorname{recovery}_{i,q}
= \mathbf{1}_{\{\tau_i \in q\}} R_i F_i
$$

Principal at maturity is:

$$
\operatorname{principal}_{i,q}
= \mathbf{1}_{\{q=\mathrm{final}\}}\mathbf{1}_{\{\tau_i>T\}}F_i
$$

Total collateral cash available in period $q$ is:

$$
C_q =
\sum_i \operatorname{coupon}_{i,q}
+ \sum_i \operatorname{recovery}_{i,q}
+ \sum_i \operatorname{principal}_{i,q}
$$

Collateral par outstanding after defaults is:

$$
\operatorname{Par}_q =
\sum_i \mathbf{1}_{\{\tau_i>t_q\}}F_i
$$

Collateral interest for coverage tests is usually:

$$
\operatorname{Interest}_q =
\sum_i \mathbf{1}_{\{\tau_i>t_{q-1}\}}c_iF_i\Delta
$$

The exact timing convention must be declared in `DealConfig`.

## 9. Simple Waterfall

The academic baseline waterfall pays:

1. Class A interest
2. Class B interest
3. Residual to equity

For tranche $j$, interest due in period $q$ is:

$$
I_{j,q}
= r_j N_{j,q-1}\Delta
+ \operatorname{carried\_shortfall}_{j,q-1}
$$

Payment is:

$$
P_{j,q}^{\mathrm{interest}}
= \min\left(\operatorname{available\_cash}, I_{j,q}\right)
$$

Unpaid interest shortfall is:

$$
\operatorname{shortfall}_{j,q}
= I_{j,q} - P_{j,q}^{\mathrm{interest}}
$$

Remaining cash after debt interest goes to equity:

$$
\operatorname{Equity}_q
= \max\left(\operatorname{available\_cash\_after\_debt\_interest}, 0\right)
$$

In the academic baseline, tranche principal repayment and loss allocation are measured through end-of-horizon collateral losses. In the industry cash-flow version, principal paydowns and writedowns are tracked directly through the waterfall.

## 10. OC and IC Tests

### 10.1 Overcollateralization Test

For senior tranche A:

$$
\operatorname{OC}_q
= \frac{\operatorname{collateral\_par}_q}
{\operatorname{senior\_notional\_outstanding}_q}
$$

The test passes if:

$$
\operatorname{OC}_q \ge \operatorname{OC}_{\mathrm{trigger}}
$$

If the test fails, residual cash that would otherwise go to mezzanine/equity may be diverted to pay down senior principal until the test is cured or cash is exhausted.

### 10.2 Interest Coverage Test

$$
\operatorname{IC}_q
= \frac{\operatorname{collateral\_interest}_q}
{\operatorname{senior\_interest\_due}_q}
$$

The test passes if:

$$
\operatorname{IC}_q \ge \operatorname{IC}_{\mathrm{trigger}}
$$

If the test fails, available residual cash is diverted to senior deleveraging, subject to the deal's priority of payments.

### 10.3 Diversion Amount

A simple v1 diversion rule is:

$$
\operatorname{diversion}_q
= \operatorname{available\_cash\_after\_senior\_interest}
$$

when either OC or IC fails. Senior principal paydown is:

$$
\operatorname{paydown}_{A,q}
= \min\left(\operatorname{diversion}_q, N_{A,q-1}\right)
$$

$$
N_{A,q} = N_{A,q-1} - \operatorname{paydown}_{A,q}
$$

Real deal documents can define different cure mechanics. The chosen convention must be explicit.

## 11. Tranche Loss Allocation

Let total portfolio loss at horizon be:

$$
L = \sum_i \mathbf{1}_{\{\tau_i \le T\}}\mathrm{LGD}_iF_i
$$

For an attachment point $A_j$ and detachment point $D_j$, tranche loss is:

$$
\operatorname{TL}_j
= \min\left(\max(L-A_j,0),D_j-A_j\right)
$$

As a percentage of tranche notional:

$$
\operatorname{tl}_j
= \frac{\operatorname{TL}_j}{D_j-A_j}
$$

For named tranche notionals in the academic structure, losses are allocated in reverse seniority:

```text
equity absorbs first
then Class B
then Class A
```

If the capital structure has:

$$
N_E = \text{equity notional},\qquad
N_B = \text{Class B notional},\qquad
N_A = \text{Class A notional}
$$

then:

$$
\operatorname{Loss}_E = \min(L,N_E)
$$

$$
\operatorname{Loss}_B = \min\left(\max(L-N_E,0),N_B\right)
$$

$$
\operatorname{Loss}_A =
\min\left(\max(L-N_E-N_B,0),N_A\right)
$$

## 12. Tranche Metrics

For $S$ Monte Carlo scenarios and tranche $j$, define scenario loss $\operatorname{Loss}_{j,s}$.

Expected loss is:

$$
\operatorname{EL}_j
= \frac{1}{S}\sum_{s=1}^{S}
\frac{\operatorname{Loss}_{j,s}}{N_j}
$$

Probability of any principal loss is:

$$
\operatorname{PD}_j
= \frac{1}{S}\sum_{s=1}^{S}
\mathbf{1}_{\{\operatorname{Loss}_{j,s}>0\}}
$$

Mean loss amount is:

$$
\operatorname{MeanLoss}_j
= \frac{1}{S}\sum_{s=1}^{S}\operatorname{Loss}_{j,s}
$$

Loss standard error is:

$$
\operatorname{SE}(\operatorname{MeanLoss}_j)
= \frac{\operatorname{sample\_std}(\operatorname{Loss}_{j,s})}{\sqrt{S}}
$$

For expected loss percentage:

$$
\operatorname{SE}(\operatorname{EL}_j)
= \frac{\operatorname{SE}(\operatorname{MeanLoss}_j)}{N_j}
$$

A normal-approximate 95% confidence interval is:

$$
\operatorname{EL}_j
\pm 1.96\,\operatorname{SE}(\operatorname{EL}_j)
$$

For low-probability senior losses, the engine should report the number of loss scenarios and warn when tail estimates are based on very few observations.

## 13. Valuation

For tranche $j$, scenario cash flows are $\operatorname{CF}_{j,q,s}$. Discount factor for period $q$ is $\operatorname{DF}_j(t_q)$.

Scenario present value:

$$
\operatorname{PV}_{j,s}
= \sum_q \operatorname{CF}_{j,q,s}\operatorname{DF}_j(t_q)
$$

Tranche value:

$$
\operatorname{Value}_j
= \frac{1}{S}\sum_{s=1}^{S}\operatorname{PV}_{j,s}
$$

If using a flat discount rate $d_j$:

$$
\operatorname{DF}_j(t_q) = e^{-d_jt_q}
$$

or, with periodic compounding:

$$
\operatorname{DF}_j(t_q)
= \frac{1}{(1+d_j\Delta)^q}
$$

The convention must be explicit. The design target is:

$$
d_A = r_{\mathrm{risk\ free}} + 50\text{ bp}
$$

$$
d_B = r_{\mathrm{Treasury}} + 400\text{ bp}
$$

Equity value is the discounted value of residual cash flows, plus reported IRR.

## 14. Equity ROE and IRR

Let the retained equity investment be $E_0$. Let expected equity cash flow at period $q$ be:

$$
\operatorname{ECF}_q
= \frac{1}{S}\sum_{s=1}^{S}\operatorname{CF}_{\mathrm{equity},q,s}
$$

Simple total return is:

$$
\operatorname{TotalReturn}
= \frac{\sum_q \operatorname{ECF}_q - E_0}{E_0}
$$

ROE may be reported as:

$$
\operatorname{ROE}
= \frac{\sum_q \operatorname{ECF}_q}{E_0}
$$

or as net return:

$$
\operatorname{NetROE}
= \frac{\sum_q \operatorname{ECF}_q - E_0}{E_0}
$$

The report must label which one is used.

IRR solves:

$$
0 = -E_0 + \sum_q \frac{\operatorname{ECF}_q}{(1+\operatorname{IRR})^{t_q}}
$$

If cash flows have multiple sign changes, IRR may be unstable; in that case report NPV at a chosen discount rate as the primary measure.

## 15. Academic Rating Mode

The academic rating mode solves for the largest Class A notional such that expected loss remains below the assigned threshold.

Let the threshold for Aa be:

$$
\theta_{\mathrm{Aa}}
$$

The condition is:

$$
\operatorname{EL}_A(N_A) \le \theta_{\mathrm{Aa}}
$$

The solver searches over $N_A$:

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

$$
N_A^* = \operatorname{low}
$$

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

Weighted-average life for tranche $j$ is:

$$
\operatorname{WAL}_j
= \frac{\sum_q t_q \operatorname{principal\_payment}_{j,q}}
{\sum_q \operatorname{principal\_payment}_{j,q}}
$$

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

$$
\operatorname{SE}(\bar{X})
= \frac{\operatorname{sample\_std}(X)}{\sqrt{S}}
$$

Convergence should be checked by running increasing scenario counts:

$$
S \in \{1{,}000,\ 5{,}000,\ 10{,}000,\ 50{,}000\}
$$

Standard errors should shrink approximately as:

$$
\operatorname{SE}_S \propto \frac{1}{\sqrt{S}}
$$

## 18. Validation Identities

### 18.1 Latent Correlation

Across simulated scenarios:

$$
\operatorname{Corr}(Y_i,Y_k) \to \rho
$$

This validates the Gaussian copula construction.

### 18.2 Marginal Default Frequency

For each name and horizon:

$$
\frac{1}{S}\sum_{s=1}^{S}\mathbf{1}_{\{\tau_{i,s}\le t\}}
\to Q_i(t)
$$

### 18.3 Joint Default Probability

For two names with identical default threshold:

$$
c = \Phi^{-1}(Q(t))
$$

the joint default probability is:

$$
\mathbb{P}(\text{default}_i,\text{ default}_k)
= \Phi_2(c,c;\rho)
$$

where $\Phi_2$ is the bivariate normal CDF with correlation $\rho$.

The default-event correlation is:

$$
\operatorname{Corr}(\mathbf{1}_i,\mathbf{1}_k)
=
\frac{\Phi_2(c,c;\rho)-Q(t)^2}
{Q(t)(1-Q(t))}
$$

This is not equal to latent correlation $\rho$ except in special cases.

### 18.4 Edge Cases

The engine must pass:

$$
Q(t)=0 \quad \Rightarrow \quad \text{no defaults}
$$

$$
Q(t)=1,\ R=0 \quad \Rightarrow \quad \text{full deterministic collateral loss}
$$

$$
\rho=0 \quad \Rightarrow \quad \text{independent defaults}
$$

$$
\text{single-name portfolio} \quad \Rightarrow \quad \text{exact Bernoulli loss distribution}
$$

$$
\mathrm{LGD}=0 \quad \Rightarrow \quad \text{no principal losses}
$$

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
