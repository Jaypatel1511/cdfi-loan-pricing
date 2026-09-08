"""Data structures and constants for CDFI loan pricing."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from cdfipricing.data.units import render


@dataclass
class LoanRequest:
    """Represents a loan being priced.

    Attributes:
        loan_amount: Principal in dollars.
        term_years: Loan term in years.
        amortization_years: Amortization period (may differ from term for balloon loans).
        sector: Borrower sector. Must be a key of SECTOR_DEFAULT_RATES.
        ltv: Loan-to-value ratio as a decimal (e.g. 0.80 = 80%).
        dscr_at_origination: Debt service coverage ratio at origination.
        borrower_credit_score: FICO or equivalent score.
        geographic_distress_level: 'low', 'medium', 'high', or 'severe'.
    """

    loan_amount: float
    term_years: int
    amortization_years: int
    sector: str
    ltv: float
    dscr_at_origination: float
    borrower_credit_score: int
    geographic_distress_level: str = "medium"

    def __post_init__(self) -> None:
        if self.loan_amount <= 0:
            raise ValueError("loan_amount must be positive")
        if self.term_years <= 0:
            raise ValueError("term_years must be positive")
        if self.amortization_years < self.term_years:
            raise ValueError("amortization_years must be >= term_years")
        if not 0 < self.ltv <= 1.0:
            raise ValueError("ltv must be between 0 and 1")
        if self.dscr_at_origination <= 0:
            raise ValueError("dscr_at_origination must be positive")
        if self.sector not in SECTOR_DEFAULT_RATES:
            raise ValueError(
                f"sector must be one of {sorted(SECTOR_DEFAULT_RATES)}; "
                f"got {self.sector!r}"
            )
        if self.geographic_distress_level not in DISTRESS_RISK_PREMIUMS:
            raise ValueError(
                f"geographic_distress_level must be one of {list(DISTRESS_RISK_PREMIUMS)}"
            )


@dataclass
class CDFICostStructure:
    """Represents a CDFI's funding and operating cost structure.

    Attributes:
        cost_of_funds: Weighted average cost of borrowed capital (decimal).
        target_roaa: Target return on average assets (decimal).
        target_roae: Target return on average equity (decimal).
        admin_cost_pct: Operating/admin costs as % of average loan balance.
        loan_loss_reserve_rate: Annual provision for loan losses as % of portfolio.
        capital_charge_rate: Required equity capital as % of loans (leverage ratio).
        fee_income_pct: Net fee income as % of loan balance (reduces required rate).
    """

    cost_of_funds: float
    target_roaa: float
    target_roae: float
    admin_cost_pct: float
    loan_loss_reserve_rate: float
    capital_charge_rate: float
    fee_income_pct: float = 0.0

    def __post_init__(self) -> None:
        if self.cost_of_funds < 0:
            raise ValueError("cost_of_funds cannot be negative")
        if self.admin_cost_pct < 0:
            raise ValueError("admin_cost_pct cannot be negative")
        if self.loan_loss_reserve_rate < 0:
            raise ValueError("loan_loss_reserve_rate cannot be negative")
        if not 0 < self.capital_charge_rate <= 1.0:
            raise ValueError("capital_charge_rate must be between 0 and 1")


@dataclass
class PricingResult:
    """Output of the loan pricing model.

    Attributes:
        recommended_rate: Final recommended loan rate (decimal).
        breakeven_rate: Minimum rate where CDFI breaks even.
        target_rate: Rate that achieves target ROAA.
        components_dict: Breakdown of each rate component.
        profitability_metrics: Key financial metrics at the recommended rate.
    """

    recommended_rate: float
    breakeven_rate: float
    target_rate: float
    components_dict: Dict[str, float]
    profitability_metrics: Dict[str, Any]

    #: Headline fields rendered above the component breakdown, in order.
    HEADLINE_FIELDS = ("recommended_rate", "breakeven_rate", "target_rate")

    def rendered_fields(self) -> Dict[str, str]:
        """Return every field ``summary()`` renders, mapped to its rendering.

        The keys are derived from this instance, so a field added to
        ``components_dict`` or ``profitability_metrics`` appears here without
        any list needing to be updated.
        """
        out: Dict[str, str] = {}
        for name in self.HEADLINE_FIELDS:
            out[name] = render(name, getattr(self, name))
        for name, val in self.components_dict.items():
            out[name] = render(name, val)
        for name, val in self.profitability_metrics.items():
            out[name] = render(name, val)
        return out

    def summary(self) -> str:
        """Return a human-readable pricing summary.

        Every value is formatted according to its unit as declared in
        :data:`cdfipricing.data.units.UNIT_REGISTRY` — never inferred from
        the value's Python type. Dollar figures render as currency, rates as
        percentages, flags as booleans.
        """
        lines = [
            "CDFI Loan Pricing Summary",
            "=" * 40,
            f"  Recommended rate : {render('recommended_rate', self.recommended_rate)}",
            f"  Breakeven rate   : {render('breakeven_rate', self.breakeven_rate)}",
            f"  Target rate      : {render('target_rate', self.target_rate)}",
            "",
            "Rate Components:",
        ]
        for name, val in self.components_dict.items():
            lines.append(f"  {name:<28} {render(name, val)}")
        lines += [
            "",
            "Profitability Metrics:",
        ]
        for name, val in self.profitability_metrics.items():
            lines.append(f"  {name:<28} {render(name, val)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECTOR_DEFAULT_RATES: Dict[str, float] = {
    "small_business": 0.0200,
    "affordable_housing": 0.0150,
    "community_facility": 0.0180,
    "healthcare": 0.0170,
    "charter_school": 0.0160,
    "mixed_use": 0.0190,
    "agriculture": 0.0210,
    "child_care": 0.0165,
    "food_system": 0.0195,
    "workforce_development": 0.0175,
}
"""Expected-loss default rate assumptions by sector (annual, decimal)."""

DISTRESS_RISK_PREMIUMS: Dict[str, float] = {
    "low": 0.0000,
    "medium": 0.0025,
    "high": 0.0050,
    "severe": 0.0100,
}
"""Additional risk premium for geographic distress level (decimal)."""

RISK_TIER_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "tier_1": {
        "min_dscr": 1.35,
        "max_ltv": 0.65,
        "min_credit_score": 700,
        "risk_premium": 0.0000,
    },
    "tier_2": {
        "min_dscr": 1.20,
        "max_ltv": 0.75,
        "min_credit_score": 650,
        "risk_premium": 0.0050,
    },
    "tier_3": {
        "min_dscr": 1.10,
        "max_ltv": 0.85,
        "min_credit_score": 600,
        "risk_premium": 0.0125,
    },
    "tier_4": {
        "min_dscr": 1.00,
        "max_ltv": 0.95,
        "min_credit_score": 550,
        "risk_premium": 0.0250,
    },
}
"""Risk tier definitions with thresholds and associated pricing premiums."""
