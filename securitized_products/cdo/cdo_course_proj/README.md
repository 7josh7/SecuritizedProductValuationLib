# Simplified CDO analysis
## The underlying assets
A bank has placed 10 speculative grade corporate bonds in a CDO it is looking to sell.  
Each bond is 5 years in duration, makes quarterly coupon payments at an annual coupon rate of 6%, and the annual default probability is 4%.  The LGD is 60% for all bonds.  The market YTM on the bonds is 9%, and the risk-free interest rate is 1% per year.  The “correlation” between any two bonds’ default dates is equal to a constant of 0.20.  Since bond defaults are modeled as geometric, the correlation needs to be properly defined.  The bonds’ face values are $10 MM each.
## The CDO
The structuring group has proposed two PACs for the CDO.  The Class A tranche has an initial notional value of $20 MM and a coupon rate of 2% per year.  The Class B tranche has a notional value of $10 MM and a coupon rate of 4% per year.  The bank will retain the residuals as equity.
## The Waterfall
The waterfall is as follows:  Class A is paid first from available cash flows, and then Class B is paid.  The residual goes to the bank.  There are no carry-forwards, all cash flows are distributed as earned.
## Task 1.
Build a simulation model of the aggregate quarterly cash flows of the portfolio, as a function of the quarterly cash flows.
## Task 2.
Apply the waterfall rules to determine the cash flow patterns to each class.
## Task 3.
The target credit rating for the Class A is Moody’s Aa.  What is the highest notional value of tranche A that will support that rating? 
