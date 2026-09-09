"""Runnable quickstart for cdfi-loan-pricing.

This file is the single source of truth for the README's Quickstart section.
Both the code and its output are spliced into README.md by
``scripts/gen_readme.py``; ``tests/test_readme_quickstart.py`` fails if the
README drifts from what this script actually prints.
"""

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
