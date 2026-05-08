"""Tests for breakeven, target rate, recommend_rate, and sensitivity analysis."""

import pytest
from cdfipricing.models.pricing import (
    compute_breakeven_rate,
    compute_target_rate,
    recommend_rate,
    sensitivity_analysis,
)
from cdfipricing.models.components import (
    cost_of_funds_component,
    expected_loss_component,
    admin_cost_component,
    capital_charge_component,
)


class TestComputeBreakevenRate:
    def test_breakeven_is_sum_of_components(self, standard_loan, standard_cost_structure):
        expected = (
            cost_of_funds_component(standard_cost_structure)
            + expected_loss_component(standard_loan, standard_cost_structure)
            + admin_cost_component(standard_cost_structure)
            + capital_charge_component(standard_cost_structure)
        )
        assert compute_breakeven_rate(standard_loan, standard_cost_structure) == pytest.approx(expected)

    def test_breakeven_positive(self, standard_loan, standard_cost_structure):
        assert compute_breakeven_rate(standard_loan, standard_cost_structure) > 0

    def test_low_risk_loan_lower_breakeven(self, low_risk_loan, standard_loan, standard_cost_structure):
        low_be = compute_breakeven_rate(low_risk_loan, standard_cost_structure)
        std_be = compute_breakeven_rate(standard_loan, standard_cost_structure)
        assert low_be < std_be

    def test_high_cost_structure_raises_breakeven(
        self, standard_loan, standard_cost_structure, high_cost_structure
    ):
        low_be = compute_breakeven_rate(standard_loan, standard_cost_structure)
        high_be = compute_breakeven_rate(standard_loan, high_cost_structure)
        assert high_be > low_be


class TestComputeTargetRate:
    def test_target_exceeds_breakeven(self, standard_loan, standard_cost_structure):
        target = compute_target_rate(standard_loan, standard_cost_structure)
        breakeven = compute_breakeven_rate(standard_loan, standard_cost_structure)
        assert target >= breakeven

    def test_target_rate_positive(self, standard_loan, standard_cost_structure):
        assert compute_target_rate(standard_loan, standard_cost_structure) > 0

    def test_higher_target_roaa_raises_rate(self, standard_loan, standard_cost_structure):
        import dataclasses
        cs_high = dataclasses.replace(standard_cost_structure, target_roaa=0.0200)
        rate_low = compute_target_rate(standard_loan, standard_cost_structure)
        rate_high = compute_target_rate(standard_loan, cs_high)
        assert rate_high > rate_low

    def test_high_risk_loan_higher_target(self, high_risk_loan, standard_loan, standard_cost_structure):
        high_rate = compute_target_rate(high_risk_loan, standard_cost_structure)
        std_rate = compute_target_rate(standard_loan, standard_cost_structure)
        assert high_rate > std_rate


class TestRecommendRate:
    def test_returns_pricing_result(self, standard_loan, standard_cost_structure):
        from cdfipricing.data.schema import PricingResult
        result = recommend_rate(standard_loan, standard_cost_structure)
        assert isinstance(result, PricingResult)

    def test_recommended_equals_target_unconstrained(self, standard_loan, standard_cost_structure):
        result = recommend_rate(standard_loan, standard_cost_structure)
        assert result.recommended_rate == pytest.approx(result.target_rate)

    def test_floor_enforced(self, standard_loan, standard_cost_structure):
        result = recommend_rate(standard_loan, standard_cost_structure, floor_rate=0.99)
        assert result.recommended_rate == pytest.approx(0.99)

    def test_ceiling_enforced(self, standard_loan, standard_cost_structure):
        result = recommend_rate(standard_loan, standard_cost_structure, ceiling_rate=0.001)
        assert result.recommended_rate == pytest.approx(0.001)

    def test_profitability_metrics_present(self, standard_loan, standard_cost_structure):
        result = recommend_rate(standard_loan, standard_cost_structure)
        for key in ("net_interest_margin", "spread_over_breakeven", "estimated_roaa"):
            assert key in result.profitability_metrics

    def test_components_dict_present(self, standard_loan, standard_cost_structure):
        result = recommend_rate(standard_loan, standard_cost_structure)
        assert "cost_of_funds" in result.components_dict
        assert "expected_loss" in result.components_dict

    def test_summary_callable(self, standard_loan, standard_cost_structure):
        result = recommend_rate(standard_loan, standard_cost_structure)
        s = result.summary()
        assert len(s) > 50

    def test_low_cost_structure_lower_rate(
        self, standard_loan, low_cost_structure, high_cost_structure
    ):
        low_result = recommend_rate(standard_loan, low_cost_structure)
        high_result = recommend_rate(standard_loan, high_cost_structure)
        assert low_result.recommended_rate < high_result.recommended_rate

    def test_meets_target_roaa_flag(self, standard_loan, standard_cost_structure):
        result = recommend_rate(standard_loan, standard_cost_structure)
        # At recommended = target rate, should meet ROAA
        assert result.profitability_metrics["meets_target_roaa"] is True

    def test_below_breakeven_not_profitable(self, standard_loan, standard_cost_structure):
        breakeven = compute_breakeven_rate(standard_loan, standard_cost_structure)
        result = recommend_rate(standard_loan, standard_cost_structure, ceiling_rate=breakeven * 0.5)
        assert result.profitability_metrics["spread_over_breakeven"] < 0


class TestSensitivityAnalysis:
    def test_cost_of_funds_sensitivity(self, standard_loan, standard_cost_structure):
        values = [0.02, 0.03, 0.04, 0.05]
        rows = sensitivity_analysis(standard_loan, standard_cost_structure, "cost_of_funds", values)
        assert len(rows) == 4
        rates = [r["recommended_rate"] for r in rows]
        assert rates == sorted(rates)

    def test_loan_loss_reserve_sensitivity(self, standard_loan, standard_cost_structure):
        values = [0.005, 0.010, 0.020, 0.040]
        rows = sensitivity_analysis(standard_loan, standard_cost_structure, "loan_loss_reserve_rate", values)
        rates = [r["recommended_rate"] for r in rows]
        assert rates == sorted(rates)

    def test_ltv_sensitivity(self, standard_loan, standard_cost_structure):
        values = [0.50, 0.65, 0.75, 0.90]
        rows = sensitivity_analysis(standard_loan, standard_cost_structure, "ltv", values)
        rates = [r["recommended_rate"] for r in rows]
        assert rates == sorted(rates)

    def test_dscr_sensitivity(self, standard_loan, standard_cost_structure):
        values = [1.05, 1.15, 1.25, 1.40]
        rows = sensitivity_analysis(standard_loan, standard_cost_structure, "dscr_at_origination", values)
        rates = [r["recommended_rate"] for r in rows]
        # Lower DSCR → higher rate
        assert rates == sorted(rates, reverse=True)

    def test_invalid_variable_raises(self, standard_loan, standard_cost_structure):
        with pytest.raises(ValueError, match="variable must be one of"):
            sensitivity_analysis(standard_loan, standard_cost_structure, "bad_var", [0.01])

    def test_rows_contain_all_keys(self, standard_loan, standard_cost_structure):
        rows = sensitivity_analysis(standard_loan, standard_cost_structure, "target_roaa", [0.005, 0.01])
        for row in rows:
            for key in ("value", "breakeven_rate", "target_rate", "recommended_rate"):
                assert key in row
