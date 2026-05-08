"""Tests for scenario comparison and market rate benchmarking."""

import pytest
from cdfipricing.analysis.comparison import compare_pricing_scenarios, market_rate_comparison
from cdfipricing.scenarios.builder import cdfi_standard_scenarios


class TestComparePricingScenarios:
    def test_returns_list(self, standard_loan):
        scenarios = cdfi_standard_scenarios()
        rows = compare_pricing_scenarios(standard_loan, scenarios)
        assert isinstance(rows, list)
        assert len(rows) == len(scenarios)

    def test_sorted_by_rate(self, standard_loan):
        scenarios = cdfi_standard_scenarios()
        rows = compare_pricing_scenarios(standard_loan, scenarios)
        rates = [r["recommended_rate"] for r in rows]
        assert rates == sorted(rates)

    def test_all_required_keys(self, standard_loan):
        scenarios = cdfi_standard_scenarios()
        rows = compare_pricing_scenarios(standard_loan, scenarios)
        for row in rows:
            for key in ("scenario", "recommended_rate", "breakeven_rate", "cost_of_funds"):
                assert key in row

    def test_scenario_names_preserved(self, standard_loan):
        scenarios = cdfi_standard_scenarios()
        rows = compare_pricing_scenarios(standard_loan, scenarios)
        names = {r["scenario"] for r in rows}
        assert names == set(scenarios.keys())

    def test_single_scenario(self, standard_loan, standard_cost_structure):
        rows = compare_pricing_scenarios(standard_loan, {"test": standard_cost_structure})
        assert len(rows) == 1
        assert rows[0]["scenario"] == "test"


class TestMarketRateComparison:
    def test_keys_present(self, standard_loan, standard_cost_structure):
        result = market_rate_comparison(standard_loan, standard_cost_structure, 0.10)
        for key in ("cdfi_rate", "market_rate", "discount_to_market", "is_below_market",
                    "mission_subsidy_bps"):
            assert key in result

    def test_below_market_when_lower(self, standard_loan, standard_cost_structure):
        result = market_rate_comparison(standard_loan, standard_cost_structure, 0.20)
        assert result["is_below_market"] is True
        assert result["discount_to_market"] > 0

    def test_above_market_flag(self, standard_loan, standard_cost_structure):
        result = market_rate_comparison(standard_loan, standard_cost_structure, market_rate=0.001)
        assert result["is_below_market"] is False

    def test_subsidy_bps_correct(self, standard_loan, standard_cost_structure):
        result = market_rate_comparison(standard_loan, standard_cost_structure, 0.10)
        expected_bps = result["discount_to_market"] * 10_000
        assert result["mission_subsidy_bps"] == pytest.approx(expected_bps, abs=0.2)

    def test_annual_subsidy_dollars(self, standard_loan, standard_cost_structure):
        result = market_rate_comparison(standard_loan, standard_cost_structure, 0.10)
        expected = result["discount_to_market"] * standard_loan.loan_amount
        assert result["annual_subsidy_dollars"] == pytest.approx(expected)

    def test_spread_to_prime(self, standard_loan, standard_cost_structure):
        result = market_rate_comparison(standard_loan, standard_cost_structure, 0.10, prime_rate=0.085)
        assert result["spread_to_prime"] == pytest.approx(result["cdfi_rate"] - 0.085)
