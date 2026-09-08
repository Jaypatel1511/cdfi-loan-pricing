"""
cdfi-loan-pricing: CDFI loan pricing model.

Cost of capital, target ROAA, expected loss, and admin cost analysis
to compute minimum viable loan rate.
"""

from cdfipricing.data.schema import (
    LoanRequest,
    CDFICostStructure,
    PricingResult,
    SECTOR_DEFAULT_RATES,
    DISTRESS_RISK_PREMIUMS,
    RISK_TIER_THRESHOLDS,
)
from cdfipricing.data.units import (
    Unit,
    UndeclaredUnitError,
    UNIT_REGISTRY,
    unit_for,
    render,
)
from cdfipricing.models.components import (
    cost_of_funds_component,
    expected_loss_component,
    admin_cost_component,
    capital_charge_component,
    target_return_component,
    risk_tier,
    risk_tier_premium,
    all_components,
)
from cdfipricing.models.pricing import (
    compute_breakeven_rate,
    compute_target_rate,
    recommend_rate,
    sensitivity_analysis,
)
from cdfipricing.scenarios.builder import cdfi_standard_scenarios
from cdfipricing.analysis.profitability import (
    loan_profitability,
    portfolio_profitability,
    cross_subsidy_analysis,
)
from cdfipricing.analysis.comparison import (
    compare_pricing_scenarios,
    market_rate_comparison,
)

__version__ = "0.2.0"

__all__ = [
    # Data
    "LoanRequest",
    "CDFICostStructure",
    "PricingResult",
    "SECTOR_DEFAULT_RATES",
    "DISTRESS_RISK_PREMIUMS",
    "RISK_TIER_THRESHOLDS",
    # Units
    "Unit",
    "UndeclaredUnitError",
    "UNIT_REGISTRY",
    "unit_for",
    "render",
    # Components
    "cost_of_funds_component",
    "expected_loss_component",
    "admin_cost_component",
    "capital_charge_component",
    "target_return_component",
    "risk_tier",
    "risk_tier_premium",
    "all_components",
    # Pricing
    "compute_breakeven_rate",
    "compute_target_rate",
    "recommend_rate",
    "sensitivity_analysis",
    # Scenarios
    "cdfi_standard_scenarios",
    # Profitability
    "loan_profitability",
    "portfolio_profitability",
    "cross_subsidy_analysis",
    # Comparison
    "compare_pricing_scenarios",
    "market_rate_comparison",
]
