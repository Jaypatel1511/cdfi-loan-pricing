"""Gates on input validation, public exports, and version-site consistency."""

import io
import os
import re

import pytest

import cdfipricing
from cdfipricing import LoanRequest, CDFICostStructure, recommend_rate
from cdfipricing.data.schema import SECTOR_DEFAULT_RATES

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _loan(**overrides):
    kwargs = dict(
        loan_amount=750_000,
        term_years=10,
        amortization_years=20,
        sector="small_business",
        ltv=0.75,
        dscr_at_origination=1.25,
        borrower_credit_score=660,
        geographic_distress_level="medium",
    )
    kwargs.update(overrides)
    return LoanRequest(**kwargs)


class TestSectorValidation:
    def test_unknown_sector_raises(self):
        with pytest.raises(ValueError) as exc:
            _loan(sector="zzz_not_a_sector")
        assert "sector" in str(exc.value)

    def test_error_names_the_offending_value(self):
        with pytest.raises(ValueError) as exc:
            _loan(sector="zzz_not_a_sector")
        assert "zzz_not_a_sector" in str(exc.value)

    def test_every_declared_sector_is_accepted(self):
        """Derived from SECTOR_DEFAULT_RATES; no sector name is typed."""
        assert SECTOR_DEFAULT_RATES
        for sector in SECTOR_DEFAULT_RATES:
            assert _loan(sector=sector).sector == sector

    def test_sectors_price_differently(self):
        """Guards the 0.1.0 symptom: an unknown sector produced output
        byte-identical to 'small_business' because the lookup silently fell
        back to a hardcoded 0.0200. Distinct declared rates must give distinct
        prices, so a silent fallback is observable.
        """
        cs = CDFICostStructure(
            cost_of_funds=0.0300,
            target_roaa=0.0075,
            target_roae=0.0450,
            admin_cost_pct=0.0300,
            loan_loss_reserve_rate=0.0150,
            capital_charge_rate=0.15,
            fee_income_pct=0.0050,
        )
        rates = {
            sector: recommend_rate(_loan(sector=sector), cs).recommended_rate
            for sector in SECTOR_DEFAULT_RATES
        }
        distinct_inputs = len(set(SECTOR_DEFAULT_RATES.values()))
        assert len(set(rates.values())) == distinct_inputs

    def test_expected_loss_has_no_silent_default(self):
        """Bypassing LoanRequest validation must fail loudly, not price at
        the hardcoded 2.00% the 0.1.0 lookup fell back to."""
        from cdfipricing.models.components import expected_loss_component

        loan = _loan()
        object.__setattr__(loan, "sector", "zzz_not_a_sector")
        cs = CDFICostStructure(0.03, 0.0075, 0.045, 0.03, 0.015, 0.15, 0.005)
        with pytest.raises(KeyError):
            expected_loss_component(loan, cs)


class TestPublicExports:
    def test_all_names_are_importable(self):
        missing = [n for n in cdfipricing.__all__ if not hasattr(cdfipricing, n)]
        assert not missing, "names in __all__ that do not exist: %r" % missing

    def test_risk_tier_is_exported(self):
        """The README claims risk-tier classification and the pricing output
        contains a 'risk_tier_premium' component; the classifier must be
        reachable from the top-level package."""
        assert "risk_tier" in cdfipricing.__all__
        assert cdfipricing.risk_tier(_loan()) in cdfipricing.RISK_TIER_THRESHOLDS

    def test_every_component_key_has_a_reachable_producer(self):
        """Derived: each components_dict key must be exported either as a
        '<key>_component' function or as '<key>' itself."""
        cs = CDFICostStructure(0.03, 0.0075, 0.045, 0.03, 0.015, 0.15, 0.005)
        keys = recommend_rate(_loan(), cs).components_dict.keys()
        assert keys
        unreachable = [
            k
            for k in keys
            if not (
                hasattr(cdfipricing, k + "_component") or hasattr(cdfipricing, k)
            )
        ]
        assert not unreachable, (
            "component keys with no exported producer: %r" % unreachable
        )


class TestVersionSitesAgree:
    """Three files carry the version. They must never disagree."""

    @staticmethod
    def _read(path):
        with io.open(os.path.join(REPO_ROOT, path), encoding="utf-8") as fh:
            return fh.read()

    def test_all_version_sites_match(self):
        found = {"cdfipricing.__version__": cdfipricing.__version__}

        m = re.search(r'^version\s*=\s*"([^"]+)"', self._read("pyproject.toml"), re.M)
        assert m, "no version found in pyproject.toml"
        found["pyproject.toml"] = m.group(1)

        m = re.search(r'version\s*=\s*"([^"]+)"', self._read("setup.py"))
        assert m, "no version found in setup.py"
        found["setup.py"] = m.group(1)

        assert len(set(found.values())) == 1, "version sites disagree: %r" % found

    def test_changelog_documents_the_current_version(self):
        text = self._read("CHANGELOG.md")
        assert "[%s]" % cdfipricing.__version__ in text, (
            "CHANGELOG.md has no entry for %s" % cdfipricing.__version__
        )
