"""Scenario comparison and market-rate benchmarking for CDFI pricing."""

from typing import Dict, List, Any

from cdfipricing.data.schema import LoanRequest, CDFICostStructure
from cdfipricing.models.pricing import recommend_rate


def compare_pricing_scenarios(
    loan: LoanRequest,
    scenarios: Dict[str, CDFICostStructure],
) -> List[Dict[str, Any]]:
    """Compare recommended rates across multiple CDFI cost-structure scenarios.

    Args:
        loan: Loan to price under each scenario.
        scenarios: Mapping of scenario name to CDFICostStructure.

    Returns:
        List of dicts sorted by recommended_rate ascending, each with:
        'scenario', 'recommended_rate', 'breakeven_rate', 'target_rate',
        and key cost components.
    """
    rows = []
    for name, cs in scenarios.items():
        result = recommend_rate(loan, cs)
        rows.append(
            {
                "scenario": name,
                "recommended_rate": result.recommended_rate,
                "breakeven_rate": result.breakeven_rate,
                "target_rate": result.target_rate,
                "cost_of_funds": result.components_dict["cost_of_funds"],
                "expected_loss": result.components_dict["expected_loss"],
                "admin_cost": result.components_dict["admin_cost"],
                "capital_charge": result.components_dict["capital_charge"],
            }
        )
    return sorted(rows, key=lambda r: r["recommended_rate"])


def market_rate_comparison(
    loan: LoanRequest,
    cost_structure: CDFICostStructure,
    market_rate: float,
    prime_rate: float = 0.0850,
    treasury_10yr: float = 0.0450,
) -> Dict[str, Any]:
    """Compare the CDFI's recommended rate against market benchmarks.

    Args:
        loan: Loan characteristics.
        cost_structure: CDFI cost structure.
        market_rate: Prevailing market rate for comparable loans.
        prime_rate: Current US prime rate (default 8.50%).
        treasury_10yr: 10-year Treasury yield (default 4.50%).

    Returns:
        Dict with:
        - 'cdfi_rate': Recommended CDFI rate.
        - 'market_rate': Provided market rate.
        - 'discount_to_market': market_rate - cdfi_rate (positive = CDFI is cheaper).
        - 'spread_to_prime': cdfi_rate - prime_rate.
        - 'spread_to_treasury': cdfi_rate - treasury_10yr.
        - 'is_below_market': True if CDFI rate < market rate.
        - 'mission_subsidy_bps': Discount to market in basis points.
    """
    result = recommend_rate(loan, cost_structure)
    cdfi_rate = result.recommended_rate

    discount = market_rate - cdfi_rate
    spread_prime = cdfi_rate - prime_rate
    spread_tsy = cdfi_rate - treasury_10yr

    return {
        "cdfi_rate": cdfi_rate,
        "breakeven_rate": result.breakeven_rate,
        "market_rate": market_rate,
        "discount_to_market": discount,
        "spread_to_prime": spread_prime,
        "spread_to_treasury": spread_tsy,
        "is_below_market": cdfi_rate < market_rate,
        "mission_subsidy_bps": round(discount * 10_000, 1),
        "annual_subsidy_dollars": discount * loan.loan_amount,
    }
