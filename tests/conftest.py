"""Shared fixtures for cdfi-loan-pricing tests."""

import pytest
from cdfipricing.data.schema import LoanRequest, CDFICostStructure


@pytest.fixture
def standard_loan():
    return LoanRequest(
        loan_amount=500_000,
        term_years=10,
        amortization_years=20,
        sector="small_business",
        ltv=0.75,
        dscr_at_origination=1.25,
        borrower_credit_score=660,
        geographic_distress_level="medium",
    )


@pytest.fixture
def low_risk_loan():
    return LoanRequest(
        loan_amount=1_000_000,
        term_years=7,
        amortization_years=20,
        sector="affordable_housing",
        ltv=0.60,
        dscr_at_origination=1.40,
        borrower_credit_score=720,
        geographic_distress_level="low",
    )


@pytest.fixture
def high_risk_loan():
    return LoanRequest(
        loan_amount=250_000,
        term_years=5,
        amortization_years=10,
        sector="agriculture",
        ltv=0.90,
        dscr_at_origination=1.05,
        borrower_credit_score=570,
        geographic_distress_level="severe",
    )


@pytest.fixture
def standard_cost_structure():
    return CDFICostStructure(
        cost_of_funds=0.0300,
        target_roaa=0.0075,
        target_roae=0.0450,
        admin_cost_pct=0.0300,
        loan_loss_reserve_rate=0.0150,
        capital_charge_rate=0.15,
        fee_income_pct=0.0050,
    )


@pytest.fixture
def low_cost_structure():
    return CDFICostStructure(
        cost_of_funds=0.0200,
        target_roaa=0.0050,
        target_roae=0.0300,
        admin_cost_pct=0.0200,
        loan_loss_reserve_rate=0.0075,
        capital_charge_rate=0.10,
        fee_income_pct=0.0100,
    )


@pytest.fixture
def high_cost_structure():
    return CDFICostStructure(
        cost_of_funds=0.0450,
        target_roaa=0.0150,
        target_roae=0.0600,
        admin_cost_pct=0.0500,
        loan_loss_reserve_rate=0.0300,
        capital_charge_rate=0.25,
        fee_income_pct=0.0025,
    )
