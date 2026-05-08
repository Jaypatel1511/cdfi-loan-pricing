"""Tests for scenario builder and standard CDFI scenarios."""

import pytest
from cdfipricing.scenarios.builder import cdfi_standard_scenarios
from cdfipricing.data.schema import CDFICostStructure
from cdfipricing.models.pricing import recommend_rate


class TestCDFIStandardScenarios:
    def test_returns_five_scenarios(self):
        scenarios = cdfi_standard_scenarios()
        assert len(scenarios) == 5

    def test_expected_keys(self):
        scenarios = cdfi_standard_scenarios()
        for key in ("rural", "urban", "healthcare", "affordable_housing", "small_business"):
            assert key in scenarios

    def test_all_are_cost_structures(self):
        scenarios = cdfi_standard_scenarios()
        for name, cs in scenarios.items():
            assert isinstance(cs, CDFICostStructure), f"{name} must be CDFICostStructure"

    def test_small_business_highest_cost_of_funds(self):
        scenarios = cdfi_standard_scenarios()
        # Small business is typically higher COF
        cofs = {k: v.cost_of_funds for k, v in scenarios.items()}
        assert cofs["small_business"] >= cofs["affordable_housing"]

    def test_affordable_housing_lowest_capital_charge(self):
        scenarios = cdfi_standard_scenarios()
        charges = {k: v.capital_charge_rate for k, v in scenarios.items()}
        assert charges["affordable_housing"] <= min(charges.values()) + 0.01

    def test_all_scenarios_produce_valid_rates(self, standard_loan):
        scenarios = cdfi_standard_scenarios()
        for name, cs in scenarios.items():
            result = recommend_rate(standard_loan, cs)
            assert 0 < result.recommended_rate < 0.30, f"Rate for {name} out of realistic range"

    def test_rural_higher_admin_than_urban(self):
        scenarios = cdfi_standard_scenarios()
        assert scenarios["rural"].admin_cost_pct >= scenarios["urban"].admin_cost_pct

    def test_all_target_roaa_positive(self):
        scenarios = cdfi_standard_scenarios()
        for name, cs in scenarios.items():
            assert cs.target_roaa > 0, f"{name} must have positive target ROAA"
