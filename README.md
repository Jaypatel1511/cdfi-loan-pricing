# cdfi-loan-pricing

![PyPI](https://img.shields.io/pypi/v/cdfi-loan-pricing)
![Python](https://img.shields.io/pypi/pyversions/cdfi-loan-pricing)
![License](https://img.shields.io/pypi/l/cdfi-loan-pricing)

**CDFI loan pricing model** — compute minimum viable loan rates from first principles: cost of capital, expected loss, admin cost, and target ROAA. Built for Community Development Financial Institutions that need transparent, component-driven pricing rather than market-rate following.

## Why

CDFIs lend into markets where credit is scarce or expensive. Pricing a loan "to market" often means either leaving money on the table or charging more than borrowers can bear. This library models pricing from the CDFI's own cost structure so you can:

- Find the true breakeven rate for any loan
- Set a rate that achieves a target return while staying mission-aligned
- Quantify the cross-subsidy your profitable loans provide to mission loans
- Run sensitivity analysis on any cost assumption

## Installation

```bash
pip install cdfi-loan-pricing
```

## Quickstart

```python
from cdfipricing import (
    LoanRequest,
    CDFICostStructure,
    recommend_rate,
    compute_breakeven_rate,
    sensitivity_analysis,
    cdfi_standard_scenarios,
    loan_profitability,
    portfolio_profitability,
    cross_subsidy_analysis,
    compare_pricing_scenarios,
    market_rate_comparison,
)

# Define a loan to price
loan = LoanRequest(
    loan_amount=750_000,
    term_years=10,
    amortization_years=20,
    sector="small_business",
    ltv=0.75,
    dscr_at_origination=1.25,
    borrower_credit_score=660,
    geographic_distress_level="medium",
)

# Define the CDFI's cost structure
cost_structure = CDFICostStructure(
    cost_of_funds=0.0300,       # 3.00% weighted average cost of debt
    target_roaa=0.0075,         # 0.75% target return on average assets
    target_roae=0.0450,         # 4.50% target return on average equity
    admin_cost_pct=0.0300,      # 3.00% annual operating cost
    loan_loss_reserve_rate=0.0150,  # 1.50% annual loan loss provision
    capital_charge_rate=0.15,   # 15% equity capital requirement
    fee_income_pct=0.0050,      # 0.50% net fee income
)

# Get the full pricing recommendation
result = recommend_rate(loan, cost_structure)
print(result.summary())
# CDFI Loan Pricing Summary
# ========================================
#   Recommended rate :  9.5775%
#   Breakeven rate   :  8.0775%
#   Target rate      :  9.5775%
# ...

# Check breakeven alone
be = compute_breakeven_rate(loan, cost_structure)
print(f"Breakeven rate: {be:.2%}")

# Sensitivity to cost of funds
rows = sensitivity_analysis(loan, cost_structure, "cost_of_funds", [0.02, 0.03, 0.04, 0.05])
for r in rows:
    print(f"CoF {r['value']:.1%} → recommended {r['recommended_rate']:.2%}")

# Use pre-built scenarios for different CDFI types
scenarios = cdfi_standard_scenarios()
comparisons = compare_pricing_scenarios(loan, scenarios)
for c in comparisons:
    print(f"{c['scenario']:22s}  {c['recommended_rate']:.2%}")

# Single-loan profitability at an actual rate
prof = loan_profitability(loan, cost_structure, actual_rate=0.085)
print(f"Net income: ${prof['net_income']:,.0f}  ROAA: {prof['roaa']:.2%}")

# Portfolio analysis
from cdfipricing import LoanRequest
loan2 = LoanRequest(500_000, 7, 15, "affordable_housing", 0.60, 1.40, 710, "low")
port = portfolio_profitability([loan, loan2], [0.085, 0.065], cost_structure)
print(f"Portfolio ROAA: {port['portfolio_roaa']:.2%}")

# Cross-subsidy: which loans subsidize which?
subsidy = cross_subsidy_analysis([loan, loan2], [0.085, 0.055], cost_structure)
print(f"Self-sustaining: {subsidy['is_self_sustaining']}")
print(f"Annual subsidy: ${subsidy['total_subsidy_amount']:,.0f}")

# Compare against market rate
mkt = market_rate_comparison(loan, cost_structure, market_rate=0.115)
print(f"Mission discount: {mkt['mission_subsidy_bps']:.0f} bps  (${mkt['annual_subsidy_dollars']:,.0f}/yr)")
```

## Key Features

- **Component-driven pricing** — cost of funds, expected loss, admin cost, capital charge, and target return each contribute a transparent, auditable slice of the rate
- **Sector-specific default rates** — 10 sectors (small business, affordable housing, healthcare, agriculture, etc.) with calibrated expected-loss assumptions
- **Geographic distress premiums** — four distress levels (low / medium / high / severe) with risk add-ons
- **Risk-tier classification** — DSCR, LTV, and credit score combine into four pricing tiers
- **Pre-built CDFI scenarios** — rural, urban, healthcare-focused, affordable housing-focused, small business-focused
- **Sensitivity analysis** — vary any cost or loan parameter and see rate impact across a range
- **Cross-subsidy analysis** — identify which loans fund mission-rate lending in your portfolio
- **Market rate benchmarking** — quantify mission discount in bps and dollars

## Use Cases

- **Loan officers** pricing individual credits against the CDFI's actual cost structure
- **CFOs** modeling the blended portfolio rate needed to sustain net asset growth
- **Board/CDFI Fund reporting** — documenting the mission subsidy embedded in below-market loans
- **Grant applications** — quantifying the subsidy value of concessionary capital
- **Scenario planning** — how does a 100 bps rise in cost of funds affect minimum viable rates?

## License

MIT © Jay Patel
