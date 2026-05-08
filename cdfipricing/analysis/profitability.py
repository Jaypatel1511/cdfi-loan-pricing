"""Loan and portfolio profitability analysis for CDFI pricing decisions."""

from typing import Dict, List, Any

from cdfipricing.data.schema import LoanRequest, CDFICostStructure
from cdfipricing.models.pricing import recommend_rate


def loan_profitability(
    loan: LoanRequest,
    cost_structure: CDFICostStructure,
    actual_rate: float,
) -> Dict[str, Any]:
    """Compute profitability metrics for a single loan at a given rate.

    Args:
        loan: Loan characteristics.
        cost_structure: CDFI cost structure.
        actual_rate: The rate actually charged on the loan.

    Returns:
        Dict with keys:
        - 'annual_interest_income': Gross interest income.
        - 'annual_fee_income': Fee income.
        - 'annual_loss_provision': Expected loss provision.
        - 'admin_cost': Operating cost allocation.
        - 'cost_of_funds': Funding cost.
        - 'net_income': Net contribution after all costs.
        - 'roaa': Return on average assets for this loan.
        - 'spread_to_breakeven': Rate minus breakeven rate.
        - 'is_profitable': True if net_income > 0.
    """
    pricing = recommend_rate(loan, cost_structure)

    annual_interest = actual_rate * loan.loan_amount
    fee_income = cost_structure.fee_income_pct * loan.loan_amount
    loss_provision = pricing.components_dict["expected_loss"] * loan.loan_amount
    admin = pricing.components_dict["admin_cost"] * loan.loan_amount
    funding_cost = pricing.components_dict["cost_of_funds"] * loan.loan_amount

    net_income = annual_interest + fee_income - loss_provision - admin - funding_cost

    return {
        "annual_interest_income": annual_interest,
        "annual_fee_income": fee_income,
        "annual_loss_provision": loss_provision,
        "admin_cost": admin,
        "cost_of_funds": funding_cost,
        "net_income": net_income,
        "roaa": net_income / loan.loan_amount,
        "spread_to_breakeven": actual_rate - pricing.breakeven_rate,
        "is_profitable": net_income > 0,
    }


def portfolio_profitability(
    loans: List[LoanRequest],
    rates: List[float],
    cost_structure: CDFICostStructure,
) -> Dict[str, Any]:
    """Aggregate profitability across a portfolio of loans.

    Args:
        loans: List of loan requests.
        rates: Corresponding actual rates charged on each loan.
        cost_structure: Shared CDFI cost structure.

    Returns:
        Dict with portfolio-level metrics: total_balance, total_net_income,
        portfolio_roaa, weighted_average_rate, loans_below_breakeven count.
    """
    if len(loans) != len(rates):
        raise ValueError("loans and rates must have the same length")

    results = [
        loan_profitability(loan, cost_structure, rate)
        for loan, rate in zip(loans, rates)
    ]

    total_balance = sum(l.loan_amount for l in loans)
    total_net_income = sum(r["net_income"] for r in results)
    total_interest = sum(r["annual_interest_income"] for r in results)
    total_fees = sum(r["annual_fee_income"] for r in results)
    total_losses = sum(r["annual_loss_provision"] for r in results)
    total_admin = sum(r["admin_cost"] for r in results)
    total_funding = sum(r["cost_of_funds"] for r in results)
    below_breakeven = sum(1 for r in results if r["spread_to_breakeven"] < 0)

    wa_rate = (
        sum(rate * loan.loan_amount for loan, rate in zip(loans, rates)) / total_balance
        if total_balance
        else 0.0
    )

    return {
        "total_balance": total_balance,
        "total_net_income": total_net_income,
        "portfolio_roaa": total_net_income / total_balance if total_balance else 0.0,
        "weighted_average_rate": wa_rate,
        "total_interest_income": total_interest,
        "total_fee_income": total_fees,
        "total_loss_provision": total_losses,
        "total_admin_cost": total_admin,
        "total_funding_cost": total_funding,
        "loans_below_breakeven": below_breakeven,
        "pct_below_breakeven": below_breakeven / len(loans) if loans else 0.0,
        "loan_count": len(loans),
    }


def cross_subsidy_analysis(
    loans: List[LoanRequest],
    rates: List[float],
    cost_structure: CDFICostStructure,
) -> Dict[str, Any]:
    """Identify which loans are cross-subsidized by which profitable loans.

    CDFIs often price some mission loans below cost, subsidized by
    higher-margin loans in the portfolio.

    Args:
        loans: List of loan requests.
        rates: Corresponding actual rates.
        cost_structure: Shared CDFI cost structure.

    Returns:
        Dict with:
        - 'subsidizing_loans': indices where spread_to_breakeven > 0.
        - 'subsidized_loans': indices where spread_to_breakeven < 0.
        - 'total_subsidy_amount': Annual dollar subsidy provided.
        - 'total_surplus_amount': Annual dollar surplus generated.
        - 'net_portfolio_position': surplus - subsidy.
        - 'is_self_sustaining': True if net position >= 0.
    """
    if len(loans) != len(rates):
        raise ValueError("loans and rates must have the same length")

    results = [
        loan_profitability(loan, cost_structure, rate)
        for loan, rate in zip(loans, rates)
    ]

    subsidizing = [i for i, r in enumerate(results) if r["spread_to_breakeven"] > 0]
    subsidized = [i for i, r in enumerate(results) if r["spread_to_breakeven"] < 0]

    total_surplus = sum(
        results[i]["spread_to_breakeven"] * loans[i].loan_amount
        for i in subsidizing
    )
    total_subsidy = abs(
        sum(
            results[i]["spread_to_breakeven"] * loans[i].loan_amount
            for i in subsidized
        )
    )
    net_position = total_surplus - total_subsidy

    return {
        "subsidizing_loans": subsidizing,
        "subsidized_loans": subsidized,
        "total_subsidy_amount": total_subsidy,
        "total_surplus_amount": total_surplus,
        "net_portfolio_position": net_position,
        "is_self_sustaining": net_position >= 0,
        "subsidy_coverage_ratio": total_surplus / total_subsidy if total_subsidy else float("inf"),
    }
