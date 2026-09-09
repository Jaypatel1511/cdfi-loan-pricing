"""Tests for individual rate component calculations."""

import pytest
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


class TestCostOfFundsComponent:
    def test_basic_calculation(self, standard_cost_structure):
        # debt fraction = 1 - 0.15 = 0.85; component = 0.03 * 0.85
        expected = 0.0300 * (1 - 0.15)
        assert cost_of_funds_component(standard_cost_structure) == pytest.approx(expected)

    def test_higher_capital_charge_lowers_component(self, standard_cost_structure, high_cost_structure):
        # More equity -> less debt -> lower cost_of_funds component per dollar
        low = cost_of_funds_component(standard_cost_structure)
        high = cost_of_funds_component(high_cost_structure)
        # High cost structure has higher COF (0.045) but also higher capital charge (0.25)
        # This test checks direction via a manual example
        import dataclasses
        cs = dataclasses.replace(standard_cost_structure, capital_charge_rate=0.30)
        lowered = cost_of_funds_component(cs)
        assert lowered < cost_of_funds_component(standard_cost_structure)

    def test_zero_fee_income_no_effect(self, standard_cost_structure):
        # fee_income_pct doesn't affect cost_of_funds_component
        import dataclasses
        cs_no_fee = dataclasses.replace(standard_cost_structure, fee_income_pct=0.0)
        assert cost_of_funds_component(cs_no_fee) == pytest.approx(
            cost_of_funds_component(standard_cost_structure)
        )


class TestExpectedLossComponent:
    def test_higher_ltv_increases_loss(self, standard_loan, standard_cost_structure):
        import dataclasses
        loan_high_ltv = dataclasses.replace(standard_loan, ltv=0.90)
        el_base = expected_loss_component(standard_loan, standard_cost_structure)
        el_high = expected_loss_component(loan_high_ltv, standard_cost_structure)
        assert el_high > el_base

    def test_lower_dscr_increases_loss(self, standard_loan, standard_cost_structure):
        import dataclasses
        loan_low_dscr = dataclasses.replace(standard_loan, dscr_at_origination=1.05)
        el_base = expected_loss_component(standard_loan, standard_cost_structure)
        el_low = expected_loss_component(loan_low_dscr, standard_cost_structure)
        assert el_low > el_base

    def test_severe_distress_increases_loss(self, standard_loan, standard_cost_structure):
        import dataclasses
        loan_severe = dataclasses.replace(standard_loan, geographic_distress_level="severe")
        el_medium = expected_loss_component(standard_loan, standard_cost_structure)
        el_severe = expected_loss_component(loan_severe, standard_cost_structure)
        assert el_severe > el_medium

    def test_reserve_rate_floor(self, standard_loan, standard_cost_structure):
        import dataclasses
        # If LLR > model estimate, LLR wins
        cs_high_llr = dataclasses.replace(standard_cost_structure, loan_loss_reserve_rate=0.99)
        el = expected_loss_component(standard_loan, cs_high_llr)
        assert el >= 0.99

    def test_sector_affects_loss(self, standard_cost_structure):
        import dataclasses
        from cdfipricing.data.schema import LoanRequest
        loan_ag = LoanRequest(
            loan_amount=200_000,
            term_years=5,
            amortization_years=10,
            sector="agriculture",
            ltv=0.70,
            dscr_at_origination=1.25,
            borrower_credit_score=660,
        )
        loan_housing = LoanRequest(
            loan_amount=200_000,
            term_years=5,
            amortization_years=10,
            sector="affordable_housing",
            ltv=0.70,
            dscr_at_origination=1.25,
            borrower_credit_score=660,
        )
        el_ag = expected_loss_component(loan_ag, standard_cost_structure)
        el_housing = expected_loss_component(loan_housing, standard_cost_structure)
        # Agriculture (0.021) > Affordable housing (0.015)
        assert el_ag > el_housing


class TestAdminCostComponent:
    def test_net_of_fee_income(self, standard_cost_structure):
        expected = 0.0300 - 0.0050
        assert admin_cost_component(standard_cost_structure) == pytest.approx(expected)

    def test_fee_exceeds_admin_floors_at_zero(self, standard_cost_structure):
        import dataclasses
        cs = dataclasses.replace(standard_cost_structure, fee_income_pct=0.05)
        assert admin_cost_component(cs) == 0.0

    def test_higher_admin_increases_component(self, standard_cost_structure):
        import dataclasses
        cs_high = dataclasses.replace(standard_cost_structure, admin_cost_pct=0.05)
        assert admin_cost_component(cs_high) > admin_cost_component(standard_cost_structure)


class TestCapitalChargeComponent:
    def test_basic_calculation(self, standard_cost_structure):
        expected = 0.0450 * 0.15
        assert capital_charge_component(standard_cost_structure) == pytest.approx(expected)

    def test_higher_capital_rate_increases_charge(self, standard_cost_structure):
        import dataclasses
        cs = dataclasses.replace(standard_cost_structure, capital_charge_rate=0.25)
        assert capital_charge_component(cs) > capital_charge_component(standard_cost_structure)


class TestRiskTier:
    def test_tier_1_loan(self, low_risk_loan):
        assert risk_tier(low_risk_loan) == "tier_1"

    def test_high_risk_loan_tier(self, high_risk_loan):
        t = risk_tier(high_risk_loan)
        assert t in ("tier_3", "tier_4")

    def test_standard_loan_tier(self, standard_loan):
        t = risk_tier(standard_loan)
        assert t in ("tier_2", "tier_3")

    def test_premium_increases_with_tier(self):
        from cdfipricing.data.schema import LoanRequest
        tier1_loan = LoanRequest(500_000, 10, 20, "small_business", 0.60, 1.40, 710)
        tier4_loan = LoanRequest(500_000, 10, 20, "small_business", 0.92, 1.02, 555)
        assert risk_tier_premium(tier1_loan) < risk_tier_premium(tier4_loan)


class TestAllComponents:
    def test_returns_all_keys(self, standard_loan, standard_cost_structure):
        comps = all_components(standard_loan, standard_cost_structure)
        for key in ("cost_of_funds", "expected_loss", "admin_cost", "capital_charge",
                    "target_return", "risk_tier_premium"):
            assert key in comps

    def test_all_non_negative(self, standard_loan, standard_cost_structure):
        comps = all_components(standard_loan, standard_cost_structure)
        for k, v in comps.items():
            assert v >= 0, f"Component {k} should be non-negative"


class TestExpectedLossDscrLadderIsNotADuplicateOfTheTierTable:
    """The DSCR breakpoints inside ``expected_loss_component`` ARE the tier
    table's ``min_dscr`` values.

    They used to be re-typed as literals (``>= 1.35 / >= 1.20 / >= 1.10``),
    so editing ``RISK_TIER_THRESHOLDS`` moved risk tiering and left expected
    loss on the old ladder — the two silently desynchronizing with no test
    failing. These gates raise each threshold in turn and require expected
    loss to follow.

    Inputs are derived from the table, and the cost structure is chosen so
    the ``max(base_el, loan_loss_reserve_rate)`` floor cannot mask the move.
    """

    @staticmethod
    def _unfloored_cost_structure(standard_cost_structure):
        import dataclasses

        return dataclasses.replace(
            standard_cost_structure, loan_loss_reserve_rate=0.0
        )

    @staticmethod
    def _loan(dscr):
        from cdfipricing.data.schema import LoanRequest

        return LoanRequest(
            loan_amount=500_000,
            term_years=10,
            amortization_years=20,
            sector="small_business",
            ltv=0.85,
            dscr_at_origination=dscr,
            borrower_credit_score=660,
            geographic_distress_level="medium",
        )

    @pytest.mark.parametrize("tier", ["tier_1", "tier_2", "tier_3"])
    def test_raising_a_tier_min_dscr_moves_expected_loss(
        self, tier, standard_cost_structure, monkeypatch
    ):
        from cdfipricing.data.schema import RISK_TIER_THRESHOLDS

        cs = self._unfloored_cost_structure(standard_cost_structure)
        threshold = RISK_TIER_THRESHOLDS[tier]["min_dscr"]
        loan = self._loan(threshold)  # exactly at the breakpoint => on the
        # favourable side of it
        before = expected_loss_component(loan, cs)
        assert before > 0, "floor not removed; gate would be vacuous"

        monkeypatch.setitem(RISK_TIER_THRESHOLDS[tier], "min_dscr", threshold + 0.10)
        after = expected_loss_component(loan, cs)
        assert after > before, (
            "%s min_dscr rose above the loan's DSCR but expected_loss did not "
            "increase (%r -> %r): the ladder is not reading the tier table"
            % (tier, before, after)
        )

    def test_the_breakpoints_are_exactly_the_tier_table_values(
        self, standard_cost_structure
    ):
        """Scan for the DSCRs at which expected loss steps, and require that
        set to equal the table's own min_dscr values. Nothing is typed."""
        from cdfipricing.data.schema import RISK_TIER_THRESHOLDS

        cs = self._unfloored_cost_structure(standard_cost_structure)
        grid = [n / 1000.0 for n in range(800, 1701)]
        breakpoints = set()
        prev = None
        for dscr in grid:
            value = expected_loss_component(self._loan(dscr), cs)
            if prev is not None and value != pytest.approx(prev):
                breakpoints.add(dscr)
            prev = value

        # The lowest min_dscr in the table is the catch-all bucket's floor,
        # not a step in the ladder; every higher one is a step.
        all_min = sorted({t["min_dscr"] for t in RISK_TIER_THRESHOLDS.values()})
        table = set(all_min[1:])
        assert table, "no thresholds inside the scanned range"
        assert min(grid) < min(table) and max(table) <= max(grid), (
            "scan range does not bracket the thresholds: %r vs %r"
            % ((min(grid), max(grid)), sorted(table))
        )
        assert breakpoints == table, (
            "expected_loss steps at %r but the tier table's min_dscr values "
            "in range are %r" % (sorted(breakpoints), sorted(table))
        )
