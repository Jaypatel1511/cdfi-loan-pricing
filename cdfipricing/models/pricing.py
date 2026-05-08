"""Core pricing functions: breakeven, target rate, recommendation, sensitivity."""

from typing import Dict, List, Any

from cdfipricing.data.schema import LoanRequest, CDFICostStructure, PricingResult
from cdfipricing.models.components import (
    cost_of_funds_component,
    expected_loss_component,
    admin_cost_component,
    capital_charge_component,
    target_return_component,
    risk_tier_premium,
    all_components,
)


def compute_breakeven_rate(
    loan: LoanRequest,
    cost_structure: CDFICostStructure,
) -> float:
    """Compute the minimum rate at which the CDFI breaks even.

    Breakeven = cost_of_funds + expected_loss + admin_cost + capital_charge
    (excludes target-return spread; does not grow net assets).

    Args:
        loan: Loan characteristics.
        cost_structure: CDFI cost structure.

    Returns:
        Breakeven rate as a decimal (e.g. 0.0650 = 6.50%).
    """
    return (
        cost_of_funds_component(cost_structure)
        + expected_loss_component(loan, cost_structure)
        + admin_cost_component(cost_structure)
        + capital_charge_component(cost_structure)
    )


def compute_target_rate(
    loan: LoanRequest,
    cost_structure: CDFICostStructure,
) -> float:
    """Compute the rate that achieves the CDFI's target ROAA.

    Target rate = breakeven + target_return_component + risk_tier_premium.

    Args:
        loan: Loan characteristics.
        cost_structure: CDFI cost structure.

    Returns:
        Target rate as a decimal.
    """
    return (
        compute_breakeven_rate(loan, cost_structure)
        + target_return_component(cost_structure)
        + risk_tier_premium(loan)
    )


def recommend_rate(
    loan: LoanRequest,
    cost_structure: CDFICostStructure,
    floor_rate: float = 0.0,
    ceiling_rate: float = 1.0,
) -> PricingResult:
    """Compute the recommended loan rate with full component breakdown.

    The recommended rate equals the target rate, clamped to [floor_rate,
    ceiling_rate] if provided.

    Args:
        loan: Loan characteristics.
        cost_structure: CDFI cost structure.
        floor_rate: Minimum allowable rate (regulatory or policy floor).
        ceiling_rate: Maximum allowable rate (usury or mission ceiling).

    Returns:
        PricingResult with recommended rate, breakeven, target, components,
        and profitability metrics.
    """
    breakeven = compute_breakeven_rate(loan, cost_structure)
    target = compute_target_rate(loan, cost_structure)
    recommended = max(floor_rate, min(ceiling_rate, target))

    components = all_components(loan, cost_structure)

    # Profitability at recommended rate
    net_interest_margin = recommended - cost_of_funds_component(cost_structure)
    spread_over_breakeven = recommended - breakeven
    annual_income = recommended * loan.loan_amount
    annual_loss_provision = expected_loss_component(loan, cost_structure) * loan.loan_amount
    net_income = (recommended - breakeven) * loan.loan_amount
    estimated_roaa = net_income / loan.loan_amount if loan.loan_amount else 0.0

    profitability = {
        "net_interest_margin": net_interest_margin,
        "spread_over_breakeven": spread_over_breakeven,
        "annual_gross_income": annual_income,
        "annual_loss_provision": annual_loss_provision,
        "net_income_estimate": net_income,
        "estimated_roaa": estimated_roaa,
        "meets_target_roaa": estimated_roaa >= cost_structure.target_roaa,
    }

    return PricingResult(
        recommended_rate=recommended,
        breakeven_rate=breakeven,
        target_rate=target,
        components_dict=components,
        profitability_metrics=profitability,
    )


def sensitivity_analysis(
    loan: LoanRequest,
    cost_structure: CDFICostStructure,
    variable: str,
    values: List[float],
) -> List[Dict[str, Any]]:
    """Show how the recommended rate changes as one input varies.

    Args:
        loan: Base loan characteristics.
        cost_structure: Base CDFI cost structure.
        variable: Which parameter to vary — one of:
            'cost_of_funds', 'loan_loss_reserve_rate', 'admin_cost_pct',
            'target_roaa', 'ltv', 'dscr_at_origination'.
        values: List of values to test for the variable.

    Returns:
        List of dicts, each with 'value', 'breakeven_rate',
        'target_rate', and 'recommended_rate'.

    Raises:
        ValueError: If variable is not supported.
    """
    supported = {
        "cost_of_funds",
        "loan_loss_reserve_rate",
        "admin_cost_pct",
        "target_roaa",
        "ltv",
        "dscr_at_origination",
    }
    if variable not in supported:
        raise ValueError(f"variable must be one of {sorted(supported)}")

    import dataclasses

    results = []
    for v in values:
        if variable in ("ltv", "dscr_at_origination"):
            test_loan = dataclasses.replace(loan, **{variable: v})
            test_cs = cost_structure
        else:
            test_loan = loan
            test_cs = dataclasses.replace(cost_structure, **{variable: v})

        result = recommend_rate(test_loan, test_cs)
        results.append(
            {
                "value": v,
                "breakeven_rate": result.breakeven_rate,
                "target_rate": result.target_rate,
                "recommended_rate": result.recommended_rate,
            }
        )
    return results
