"""Tests for data schema dataclasses and constants."""

import pytest
from cdfipricing.data.schema import (
    LoanRequest,
    CDFICostStructure,
    PricingResult,
    SECTOR_DEFAULT_RATES,
    DISTRESS_RISK_PREMIUMS,
    RISK_TIER_THRESHOLDS,
)


class TestLoanRequest:
    def test_basic_creation(self, standard_loan):
        assert standard_loan.loan_amount == 500_000
        assert standard_loan.sector == "small_business"

    def test_invalid_loan_amount(self):
        with pytest.raises(ValueError, match="loan_amount"):
            LoanRequest(
                loan_amount=-1,
                term_years=10,
                amortization_years=10,
                sector="small_business",
                ltv=0.75,
                dscr_at_origination=1.25,
                borrower_credit_score=660,
            )

    def test_invalid_term(self):
        with pytest.raises(ValueError, match="term_years"):
            LoanRequest(
                loan_amount=100_000,
                term_years=0,
                amortization_years=10,
                sector="small_business",
                ltv=0.75,
                dscr_at_origination=1.25,
                borrower_credit_score=660,
            )

    def test_amortization_less_than_term(self):
        with pytest.raises(ValueError, match="amortization_years"):
            LoanRequest(
                loan_amount=100_000,
                term_years=10,
                amortization_years=5,
                sector="small_business",
                ltv=0.75,
                dscr_at_origination=1.25,
                borrower_credit_score=660,
            )

    def test_invalid_ltv(self):
        with pytest.raises(ValueError, match="ltv"):
            LoanRequest(
                loan_amount=100_000,
                term_years=10,
                amortization_years=10,
                sector="small_business",
                ltv=1.10,
                dscr_at_origination=1.25,
                borrower_credit_score=660,
            )

    def test_invalid_distress_level(self):
        with pytest.raises(ValueError, match="geographic_distress_level"):
            LoanRequest(
                loan_amount=100_000,
                term_years=10,
                amortization_years=10,
                sector="small_business",
                ltv=0.75,
                dscr_at_origination=1.25,
                borrower_credit_score=660,
                geographic_distress_level="extreme",
            )

    def test_default_distress_level(self):
        loan = LoanRequest(
            loan_amount=100_000,
            term_years=10,
            amortization_years=10,
            sector="small_business",
            ltv=0.75,
            dscr_at_origination=1.25,
            borrower_credit_score=660,
        )
        assert loan.geographic_distress_level == "medium"


class TestCDFICostStructure:
    def test_basic_creation(self, standard_cost_structure):
        assert standard_cost_structure.cost_of_funds == 0.0300

    def test_negative_cost_of_funds(self):
        with pytest.raises(ValueError, match="cost_of_funds"):
            CDFICostStructure(
                cost_of_funds=-0.01,
                target_roaa=0.01,
                target_roae=0.05,
                admin_cost_pct=0.03,
                loan_loss_reserve_rate=0.015,
                capital_charge_rate=0.15,
            )

    def test_invalid_capital_charge_rate(self):
        with pytest.raises(ValueError, match="capital_charge_rate"):
            CDFICostStructure(
                cost_of_funds=0.03,
                target_roaa=0.01,
                target_roae=0.05,
                admin_cost_pct=0.03,
                loan_loss_reserve_rate=0.015,
                capital_charge_rate=0.0,
            )


class TestPricingResultSummary:
    def test_summary_contains_rates(self):
        result = PricingResult(
            recommended_rate=0.0750,
            breakeven_rate=0.0650,
            target_rate=0.0750,
            components_dict={"cost_of_funds": 0.025, "expected_loss": 0.020},
            profitability_metrics={"roaa": 0.0075, "meets_target_roaa": True},
        )
        summary = result.summary()
        assert "7.5000%" in summary
        assert "6.5000%" in summary
        assert "cost_of_funds" in summary


class TestConstants:
    def test_sector_rates_keys(self):
        assert "small_business" in SECTOR_DEFAULT_RATES
        assert "affordable_housing" in SECTOR_DEFAULT_RATES
        assert len(SECTOR_DEFAULT_RATES) >= 5

    def test_sector_rates_values_positive(self):
        for k, v in SECTOR_DEFAULT_RATES.items():
            assert v > 0, f"Rate for {k} must be positive"

    def test_distress_premiums_ordered(self):
        levels = ["low", "medium", "high", "severe"]
        premiums = [DISTRESS_RISK_PREMIUMS[l] for l in levels]
        assert premiums == sorted(premiums)

    def test_distress_premiums_low_is_zero(self):
        assert DISTRESS_RISK_PREMIUMS["low"] == 0.0

    def test_risk_tiers_exist(self):
        for tier in ("tier_1", "tier_2", "tier_3", "tier_4"):
            assert tier in RISK_TIER_THRESHOLDS

    def test_risk_tier_premiums_ascending(self):
        premiums = [
            RISK_TIER_THRESHOLDS[t]["risk_premium"]
            for t in ("tier_1", "tier_2", "tier_3", "tier_4")
        ]
        assert premiums == sorted(premiums)
