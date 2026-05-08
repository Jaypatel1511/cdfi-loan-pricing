"""Pre-built CDFI cost structure scenarios for common institution types."""

from typing import Dict

from cdfipricing.data.schema import CDFICostStructure


def cdfi_standard_scenarios() -> Dict[str, CDFICostStructure]:
    """Return a dict of typical CDFI cost structures by institution focus.

    Scenarios are calibrated to realistic CDFI operating benchmarks based on
    OFN Opportunity Finance Industry Analysis data.

    Returns:
        Dict mapping scenario name to CDFICostStructure. Keys:
        - 'rural': Community development lender in rural markets.
        - 'urban': Urban-market CDFI with diversified funding.
        - 'healthcare': Healthcare-focused CDFI (HRSA-funded structures).
        - 'affordable_housing': Affordable housing CDFI (LIHTC, FHLB funding).
        - 'small_business': Small business CDFI (SBA partnerships, SSBCI).
    """
    return {
        "rural": CDFICostStructure(
            cost_of_funds=0.0325,
            target_roaa=0.0100,
            target_roae=0.0500,
            admin_cost_pct=0.0350,
            loan_loss_reserve_rate=0.0200,
            capital_charge_rate=0.20,
            fee_income_pct=0.0050,
        ),
        "urban": CDFICostStructure(
            cost_of_funds=0.0275,
            target_roaa=0.0075,
            target_roae=0.0400,
            admin_cost_pct=0.0300,
            loan_loss_reserve_rate=0.0150,
            capital_charge_rate=0.15,
            fee_income_pct=0.0075,
        ),
        "healthcare": CDFICostStructure(
            cost_of_funds=0.0300,
            target_roaa=0.0075,
            target_roae=0.0450,
            admin_cost_pct=0.0325,
            loan_loss_reserve_rate=0.0125,
            capital_charge_rate=0.18,
            fee_income_pct=0.0060,
        ),
        "affordable_housing": CDFICostStructure(
            cost_of_funds=0.0250,
            target_roaa=0.0050,
            target_roae=0.0350,
            admin_cost_pct=0.0275,
            loan_loss_reserve_rate=0.0100,
            capital_charge_rate=0.12,
            fee_income_pct=0.0100,
        ),
        "small_business": CDFICostStructure(
            cost_of_funds=0.0350,
            target_roaa=0.0125,
            target_roae=0.0550,
            admin_cost_pct=0.0400,
            loan_loss_reserve_rate=0.0250,
            capital_charge_rate=0.22,
            fee_income_pct=0.0040,
        ),
    }
