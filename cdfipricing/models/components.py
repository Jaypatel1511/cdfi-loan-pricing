"""Individual rate component calculations for CDFI loan pricing."""

from typing import Dict

from cdfipricing.data.schema import (
    LoanRequest,
    CDFICostStructure,
    SECTOR_DEFAULT_RATES,
    DISTRESS_RISK_PREMIUMS,
    RISK_TIER_THRESHOLDS,
)


def cost_of_funds_component(cost_structure: CDFICostStructure) -> float:
    """Return the cost-of-funds component of the loan rate.

    This is the weighted average cost of capital the CDFI must recover
    on the debt-funded portion of the loan.

    Args:
        cost_structure: CDFI funding and operating structure.

    Returns:
        Annual cost-of-funds rate contribution (decimal).
    """
    debt_fraction = 1.0 - cost_structure.capital_charge_rate
    return cost_structure.cost_of_funds * debt_fraction


def expected_loss_component(
    loan: LoanRequest,
    cost_structure: CDFICostStructure,
) -> float:
    """Return the expected-loss component of the loan rate.

    Combines the sector baseline default rate, geographic distress premium,
    and an LTV severity adjustment to estimate annualized loss.

    Args:
        loan: Loan characteristics.
        cost_structure: CDFI cost structure (provides baseline LLR override
            if higher than sector default).

    Returns:
        Annual expected loss rate (decimal).
    """
    sector_pd = SECTOR_DEFAULT_RATES.get(loan.sector, 0.0200)
    distress_premium = DISTRESS_RISK_PREMIUMS[loan.geographic_distress_level]

    # LTV severity: higher LTV → less collateral coverage → higher loss given default
    # LGD is modeled as max(0, LTV - 0.60) as a fraction of the default rate
    lgd_multiplier = 1.0 + max(0.0, loan.ltv - 0.60) * 2.0

    # DSCR adjustment: lower DSCR → higher probability of default
    if loan.dscr_at_origination >= 1.35:
        dscr_adj = 0.80
    elif loan.dscr_at_origination >= 1.20:
        dscr_adj = 1.00
    elif loan.dscr_at_origination >= 1.10:
        dscr_adj = 1.30
    else:
        dscr_adj = 1.65

    base_el = sector_pd * lgd_multiplier * dscr_adj + distress_premium

    # Use the higher of model estimate and CDFI's own reserve rate
    return max(base_el, cost_structure.loan_loss_reserve_rate)


def admin_cost_component(cost_structure: CDFICostStructure) -> float:
    """Return the admin-cost component of the loan rate.

    Represents operating expenses (underwriting, servicing, compliance,
    mission impact reporting) net of fee income.

    Args:
        cost_structure: CDFI cost structure.

    Returns:
        Net admin cost contribution to loan rate (decimal).
    """
    return max(0.0, cost_structure.admin_cost_pct - cost_structure.fee_income_pct)


def capital_charge_component(cost_structure: CDFICostStructure) -> float:
    """Return the required equity return component of the loan rate.

    CDFIs must earn enough on the equity portion of the balance sheet
    to sustain net assets and meet grant + investor expectations.

    Args:
        cost_structure: CDFI cost structure.

    Returns:
        Equity capital charge contribution (decimal).
    """
    return cost_structure.target_roae * cost_structure.capital_charge_rate


def target_return_component(cost_structure: CDFICostStructure) -> float:
    """Return the incremental spread needed to hit target ROAA.

    After covering breakeven costs, this is the additional spread
    required to grow net assets at the target ROAA pace.

    Args:
        cost_structure: CDFI cost structure.

    Returns:
        Target-return spread (decimal).
    """
    # ROAA is applied to total assets; convert to a loan-rate add-on
    # Excess above breakeven needed to achieve the ROAA target
    return cost_structure.target_roaa


def risk_tier(loan: LoanRequest) -> str:
    """Classify a loan into a risk tier based on DSCR, LTV, and credit score.

    Args:
        loan: Loan characteristics.

    Returns:
        Tier name ('tier_1' through 'tier_4').
    """
    for tier_name in ("tier_1", "tier_2", "tier_3", "tier_4"):
        thresh = RISK_TIER_THRESHOLDS[tier_name]
        if (
            loan.dscr_at_origination >= thresh["min_dscr"]
            and loan.ltv <= thresh["max_ltv"]
            and loan.borrower_credit_score >= thresh["min_credit_score"]
        ):
            return tier_name
    return "tier_4"


def risk_tier_premium(loan: LoanRequest) -> float:
    """Return the risk-based pricing premium for the loan's risk tier.

    Args:
        loan: Loan characteristics.

    Returns:
        Risk premium (decimal).
    """
    tier = risk_tier(loan)
    return RISK_TIER_THRESHOLDS[tier]["risk_premium"]


def all_components(
    loan: LoanRequest,
    cost_structure: CDFICostStructure,
) -> Dict[str, float]:
    """Return a dictionary of all pricing components.

    Args:
        loan: Loan characteristics.
        cost_structure: CDFI cost structure.

    Returns:
        Mapping of component name to rate contribution (decimal).
    """
    return {
        "cost_of_funds": cost_of_funds_component(cost_structure),
        "expected_loss": expected_loss_component(loan, cost_structure),
        "admin_cost": admin_cost_component(cost_structure),
        "capital_charge": capital_charge_component(cost_structure),
        "target_return": target_return_component(cost_structure),
        "risk_tier_premium": risk_tier_premium(loan),
    }
