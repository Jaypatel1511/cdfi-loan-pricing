"""Tests for loan and portfolio profitability analysis."""

import pytest
from cdfipricing.analysis.profitability import (
    loan_profitability,
    portfolio_profitability,
    cross_subsidy_analysis,
)
from cdfipricing.models.pricing import compute_breakeven_rate


class TestLoanProfitability:
    def test_keys_present(self, standard_loan, standard_cost_structure):
        result = loan_profitability(standard_loan, standard_cost_structure, 0.08)
        for key in ("annual_interest_income", "net_income", "roaa", "spread_to_breakeven", "is_profitable"):
            assert key in result

    def test_rate_above_breakeven_is_profitable(self, standard_loan, standard_cost_structure):
        be = compute_breakeven_rate(standard_loan, standard_cost_structure)
        result = loan_profitability(standard_loan, standard_cost_structure, be + 0.02)
        assert result["is_profitable"] is True

    def test_rate_well_below_breakeven_not_profitable(self, standard_loan, standard_cost_structure):
        result = loan_profitability(standard_loan, standard_cost_structure, 0.001)
        assert result["is_profitable"] is False

    def test_annual_interest_correct(self, standard_loan, standard_cost_structure):
        result = loan_profitability(standard_loan, standard_cost_structure, 0.08)
        assert result["annual_interest_income"] == pytest.approx(500_000 * 0.08)

    def test_spread_to_breakeven_sign(self, standard_loan, standard_cost_structure):
        be = compute_breakeven_rate(standard_loan, standard_cost_structure)
        result_above = loan_profitability(standard_loan, standard_cost_structure, be + 0.01)
        result_below = loan_profitability(standard_loan, standard_cost_structure, be - 0.01)
        assert result_above["spread_to_breakeven"] > 0
        assert result_below["spread_to_breakeven"] < 0


class TestPortfolioProfitability:
    def _make_portfolio(self, standard_loan, low_risk_loan, standard_cost_structure):
        loans = [standard_loan, low_risk_loan]
        rates = [0.08, 0.065]
        return loans, rates

    def test_keys_present(self, standard_loan, low_risk_loan, standard_cost_structure):
        loans, rates = self._make_portfolio(standard_loan, low_risk_loan, standard_cost_structure)
        result = portfolio_profitability(loans, rates, standard_cost_structure)
        for key in ("total_balance", "portfolio_roaa", "weighted_average_rate", "loan_count"):
            assert key in result

    def test_total_balance_correct(self, standard_loan, low_risk_loan, standard_cost_structure):
        loans, rates = self._make_portfolio(standard_loan, low_risk_loan, standard_cost_structure)
        result = portfolio_profitability(loans, rates, standard_cost_structure)
        assert result["total_balance"] == pytest.approx(1_500_000)

    def test_loan_count(self, standard_loan, low_risk_loan, standard_cost_structure):
        loans, rates = self._make_portfolio(standard_loan, low_risk_loan, standard_cost_structure)
        result = portfolio_profitability(loans, rates, standard_cost_structure)
        assert result["loan_count"] == 2

    def test_mismatched_lengths_raises(self, standard_loan, standard_cost_structure):
        with pytest.raises(ValueError, match="same length"):
            portfolio_profitability([standard_loan], [0.08, 0.07], standard_cost_structure)

    def test_wa_rate_between_individual_rates(self, standard_loan, low_risk_loan, standard_cost_structure):
        loans, rates = self._make_portfolio(standard_loan, low_risk_loan, standard_cost_structure)
        result = portfolio_profitability(loans, rates, standard_cost_structure)
        assert min(rates) <= result["weighted_average_rate"] <= max(rates)


class TestCrossSubsidyAnalysis:
    def test_subsidy_structure(self, standard_loan, low_risk_loan, high_risk_loan, standard_cost_structure):
        from cdfipricing.models.pricing import compute_breakeven_rate
        be_high = compute_breakeven_rate(high_risk_loan, standard_cost_structure)
        # Price high-risk loan below breakeven, standard above
        loans = [standard_loan, high_risk_loan]
        rates = [0.12, be_high * 0.5]
        result = cross_subsidy_analysis(loans, rates, standard_cost_structure)
        assert 0 in result["subsidizing_loans"]  # standard_loan at high rate
        assert 1 in result["subsidized_loans"]   # high_risk_loan below breakeven

    def test_all_above_breakeven_no_subsidy(self, standard_loan, low_risk_loan, standard_cost_structure):
        loans = [standard_loan, low_risk_loan]
        rates = [0.15, 0.12]  # both well above breakeven
        result = cross_subsidy_analysis(loans, rates, standard_cost_structure)
        assert len(result["subsidized_loans"]) == 0
        assert result["is_self_sustaining"] is True

    def test_net_position_key_present(self, standard_loan, standard_cost_structure):
        result = cross_subsidy_analysis([standard_loan], [0.08], standard_cost_structure)
        assert "net_portfolio_position" in result
        assert "subsidy_coverage_ratio" in result

    def test_mismatched_lengths_raises(self, standard_loan, standard_cost_structure):
        with pytest.raises(ValueError, match="same length"):
            cross_subsidy_analysis([standard_loan], [0.08, 0.07], standard_cost_structure)
