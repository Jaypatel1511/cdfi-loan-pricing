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

Every figure below is generated: the code block is the verbatim source of
[`examples/quickstart.py`](examples/quickstart.py) and the output block is
that script's captured stdout. `tests/test_readme_quickstart.py` fails if
either drifts.

<!-- BEGIN GENERATED: quickstart-code -->
```python
from cdfipricing import (
    LoanRequest,
    CDFICostStructure,
    recommend_rate,
    compute_breakeven_rate,
    sensitivity_analysis,
    cdfi_standard_scenarios,
    risk_tier,
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

# Get the full pricing recommendation.
# Rates print as percentages, dollar amounts as currency — each field's unit
# is declared, never inferred from its Python type.
result = recommend_rate(loan, cost_structure)
print(result.summary())

# Check breakeven alone
be = compute_breakeven_rate(loan, cost_structure)
print(f"\nBreakeven rate: {be:.2%}")

# Which risk tier did the loan land in?
print(f"Risk tier: {risk_tier(loan)}")

# Sensitivity to cost of funds
print("\nSensitivity to cost of funds:")
rows = sensitivity_analysis(loan, cost_structure, "cost_of_funds", [0.02, 0.03, 0.04, 0.05])
for r in rows:
    print(f"  CoF {r['value']:.1%} -> recommended {r['recommended_rate']:.2%}")

# Use pre-built scenarios for different CDFI types
print("\nPre-built CDFI scenarios:")
scenarios = cdfi_standard_scenarios()
comparisons = compare_pricing_scenarios(loan, scenarios)
for c in comparisons:
    print(f"  {c['scenario']:22s}  {c['recommended_rate']:.2%}")

# Single-loan profitability at an actual rate
prof = loan_profitability(loan, cost_structure, actual_rate=0.085)
print(f"\nNet income: ${prof['net_income']:,.0f}   ROAA: {prof['roaa']:.2%}")

# Portfolio analysis
loan2 = LoanRequest(500_000, 7, 15, "affordable_housing", 0.60, 1.40, 710, "low")
port = portfolio_profitability([loan, loan2], [0.085, 0.065], cost_structure)
print(f"Portfolio ROAA: {port['portfolio_roaa']:.2%}")

# Cross-subsidy: which loans subsidize which?
subsidy = cross_subsidy_analysis([loan, loan2], [0.085, 0.055], cost_structure)
print(f"Self-sustaining: {subsidy['is_self_sustaining']}")
print(f"Annual subsidy: ${subsidy['total_subsidy_amount']:,.0f}")

# Compare against market rate
mkt = market_rate_comparison(loan, cost_structure, market_rate=0.115)
print(
    f"Mission discount: {mkt['mission_subsidy_bps']:.0f} bps "
    f"(${mkt['annual_subsidy_dollars']:,.0f}/yr)"
)
```
<!-- END GENERATED: quickstart-code -->

Output:

<!-- BEGIN GENERATED: quickstart-output -->
```text
CDFI Loan Pricing Summary
========================================
  Recommended rate : 9.8250%
  Breakeven rate   : 8.5750%
  Target rate      : 9.8250%

Rate Components:
  cost_of_funds                2.5500%
  expected_loss                2.8500%
  admin_cost                   2.5000%
  capital_charge               0.6750%
  target_return                0.7500%
  risk_tier_premium            0.5000%

Profitability Metrics:
  net_interest_margin          7.2750%
  spread_over_breakeven        1.2500%
  annual_gross_income          $73,687.50
  annual_loss_provision        $21,375.00
  net_income_estimate          $9,375.00
  estimated_roaa               1.2500%
  meets_target_roaa            True

Breakeven rate: 8.58%
Risk tier: tier_2

Sensitivity to cost of funds:
  CoF 2.0% -> recommended 8.97%
  CoF 3.0% -> recommended 9.83%
  CoF 4.0% -> recommended 10.68%
  CoF 5.0% -> recommended 11.53%

Pre-built CDFI scenarios:
  affordable_housing      8.22%
  urban                   9.29%
  healthcare              10.02%
  rural                   10.95%
  small_business          12.14%

Net income: $8,250   ROAA: 1.10%
Portfolio ROAA: 0.84%
Self-sustaining: False
Annual subsidy: $9,187
Mission discount: 168 bps ($12,562/yr)
```
<!-- END GENERATED: quickstart-output -->

## Key Features

- **Component-driven pricing** — cost of funds, expected loss, admin cost, capital charge, and target return each contribute a transparent, auditable slice of the rate
- **Sector-specific default rates** — 10 sectors (small business, affordable housing, healthcare, agriculture, etc.) with calibrated expected-loss assumptions
- **Geographic distress premiums** — four distress levels (low / medium / high / severe) with risk add-ons
- **Risk-tier classification** — DSCR, LTV, and credit score combine into four pricing tiers, exposed as `risk_tier(loan)` and `risk_tier_premium(loan)`
- **Pre-built CDFI scenarios** — rural, urban, healthcare-focused, affordable housing-focused, small business-focused
- **Sensitivity analysis** — vary any cost or loan parameter and see rate impact across a range
- **Cross-subsidy analysis** — identify which loans fund mission-rate lending in your portfolio
- **Market rate benchmarking** — quantify mission discount in bps and dollars
- **Declared units** — every field of a `PricingResult` declares whether it is a rate, a dollar amount or a flag (`cdfipricing.UNIT_REGISTRY`), so `PricingResult.summary()` cannot label its dollars as percentages. The registry is keyed by field name alone and covers `recommend_rate`'s output only: `loan_profitability` returns `admin_cost` and `cost_of_funds` as *dollars* under names the registry declares as rates, so do not call `cdfipricing.render()` on anything but a `PricingResult`. See the CHANGELOG's Known issues.

## Use Cases

- **Loan officers** pricing individual credits against the CDFI's actual cost structure
- **CFOs** modeling the blended portfolio rate needed to sustain net asset growth
- **Board/CDFI Fund reporting** — documenting the mission subsidy embedded in below-market loans
- **Grant applications** — quantifying the subsidy value of concessionary capital
- **Scenario planning** — how does a 100 bps rise in cost of funds affect minimum viable rates?

## License

MIT © Jay Patel
