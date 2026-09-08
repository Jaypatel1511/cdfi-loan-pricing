"""Gate: every quantitative claim in the current CHANGELOG entry is re-derived.

``tests/test_readme_quickstart.py`` stops hand-typed figures reaching the
README. It says nothing about the CHANGELOG — and the CHANGELOG is where this
package's quantitative claims actually live. That gap shipped a fabricated
measurement: a "48 of 3,200 unclamped inputs (1.5%)" sweep result, when the
grid the shipped test walks is 10 sectors x 4 distress levels x 4 LTVs x
4 DSCRs x 4 credit scores = 2,560 points and the count is 22 (0.86%). No one
had run it; 10 x 4 x 4 x 4 x 4 cannot be 3,200.

This module closes that gap the same way the README gate does: it computes
each figure from the package and requires the CHANGELOG to quote exactly what
came back. The completeness gate at the bottom is the important one — it
scans the whole entry and fails on any dollar amount or percentage the
derivation did not produce, so a NEW unverified figure cannot be added
silently either.
"""

import functools
import io
import os
import re
import runpy
import sys

import pytest

import cdfipricing
from cdfipricing import (
    CDFICostStructure,
    LoanRequest,
    loan_profitability,
    portfolio_profitability,
    recommend_rate,
)
from cdfipricing.data.schema import (
    DISTRESS_RISK_PREMIUMS,
    RISK_TIER_THRESHOLDS,
    SECTOR_DEFAULT_RATES,
)
from cdfipricing.data.units import render

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG = os.path.join(REPO_ROOT, "CHANGELOG.md")
EXAMPLE = os.path.join(REPO_ROOT, "examples", "quickstart.py")

needs_sources = pytest.mark.skipif(
    not (os.path.exists(CHANGELOG) and os.path.exists(EXAMPLE)),
    reason="CHANGELOG/example not present (installed-package layout)",
)


# ---------------------------------------------------------------------------
# Inputs: taken from examples/quickstart.py, the same single source the README
# is generated from. Nothing about the quickstart loan is typed here.
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=None)
def quickstart_inputs():
    """Run examples/quickstart.py and return its ``loan``, ``loan2`` and
    ``cost_structure`` objects."""
    saved, sys.stdout = sys.stdout, io.StringIO()
    try:
        ns = runpy.run_path(EXAMPLE)
    finally:
        sys.stdout = saved
    loan, loan2 = ns["loan"], ns["loan2"]
    cost_structure = ns["cost_structure"]
    assert isinstance(loan, LoanRequest) and isinstance(loan2, LoanRequest)
    assert isinstance(cost_structure, CDFICostStructure)
    return loan, loan2, cost_structure


def sweep_counts(cost_structure, loan_amount=1_000_000):
    """Re-walk the grid ``TestMeetsTargetRoaaFlag`` walks and count the loans
    a bare ``>=`` would have reported as missing target.

    The grid is derived from the package's own constants, exactly as that
    test derives it — so if a sector or a tier is ever added, the CHANGELOG's
    figures go stale and this module says so.
    """
    ltvs = sorted({t["max_ltv"] for t in RISK_TIER_THRESHOLDS.values()})
    dscrs = sorted({t["min_dscr"] for t in RISK_TIER_THRESHOLDS.values()})
    scores = sorted({int(t["min_credit_score"]) for t in RISK_TIER_THRESHOLDS.values()})

    unclamped = 0
    false_negatives = 0
    for sector in SECTOR_DEFAULT_RATES:
        for distress in DISTRESS_RISK_PREMIUMS:
            for ltv in ltvs:
                for dscr in dscrs:
                    for score in scores:
                        loan = LoanRequest(
                            loan_amount=loan_amount,
                            term_years=10,
                            amortization_years=20,
                            sector=sector,
                            ltv=ltv,
                            dscr_at_origination=dscr,
                            borrower_credit_score=score,
                            geographic_distress_level=distress,
                        )
                        res = recommend_rate(loan, cost_structure)
                        if res.recommended_rate != res.target_rate:
                            continue
                        unclamped += 1
                        roaa = res.profitability_metrics["estimated_roaa"]
                        if not roaa >= cost_structure.target_roaa:
                            false_negatives += 1
    return unclamped, false_negatives


@functools.lru_cache(maxsize=None)
def derived_figures():
    """Every dollar amount and percentage the current entry is entitled to
    quote, keyed by what it is. Values are the exact strings."""
    loan, loan2, cs = quickstart_inputs()
    result = recommend_rate(loan, cs)
    metrics = result.profitability_metrics
    prof_at_readme_rate = loan_profitability(loan, cs, actual_rate=0.085)
    prof_at_recommended = loan_profitability(loan, cs, result.recommended_rate)
    port = portfolio_profitability([loan, loan2], [0.085, 0.065], cs)
    result2 = recommend_rate(loan2, cs)

    money = "${:,.2f}".format
    unclamped, false_negatives = sweep_counts(cs)

    # The 0.1.0 renderer: ':.4%' applied to every float, dollars included.
    def as_0_1_0(value):
        return "{:.4%}".format(value)

    consistent_net_1 = (0.085 - result.breakeven_rate) * loan.loan_amount
    consistent_net_2 = (0.065 - result2.breakeven_rate) * loan2.loan_amount
    consistent_total = consistent_net_1 + consistent_net_2

    figures = {
        # --- the rendering defect, measured on the quickstart loan ---------
        "gross_income_0_1_0": as_0_1_0(metrics["annual_gross_income"]),
        "gross_income_fixed": render(
            "annual_gross_income", metrics["annual_gross_income"]
        ),
        "loss_provision_0_1_0": as_0_1_0(metrics["annual_loss_provision"]),
        "loss_provision_fixed": render(
            "annual_loss_provision", metrics["annual_loss_provision"]
        ),
        "net_income_estimate_0_1_0": as_0_1_0(metrics["net_income_estimate"]),
        "net_income_estimate_fixed": render(
            "net_income_estimate", metrics["net_income_estimate"]
        ),
        # --- the README rates the 0.1.0 docs got wrong ---------------------
        "recommended_rate": render("recommended_rate", result.recommended_rate),
        "breakeven_rate": render("breakeven_rate", result.breakeven_rate),
        # --- the silent sector fallback ------------------------------------
        "sector_fallback": "{:.2%}".format(SECTOR_DEFAULT_RATES["small_business"]),
        # --- the meets_target_roaa sweep -----------------------------------
        "sweep_false_share": "{:.2%}".format(false_negatives / unclamped),
        # --- the deferred net-income inconsistency -------------------------
        "fee_double_count": money(cs.fee_income_pct * loan.loan_amount),
        "omitted_capital_charge": money(
            result.components_dict["capital_charge"] * loan.loan_amount
        ),
        "net_income_gap": money(
            prof_at_recommended["net_income"] - metrics["net_income_estimate"]
        ),
        "loan_profitability_net": money(prof_at_recommended["net_income"]),
        "pricing_result_net": money(metrics["net_income_estimate"]),
        "loan_profitability_roaa": render("estimated_roaa", prof_at_recommended["roaa"]),
        "pricing_result_roaa": render("estimated_roaa", metrics["estimated_roaa"]),
        # --- the flipped verdict, on the README's own numbers ---------------
        "readme_actual_rate": "{:.2%}".format(0.085),
        "readme_net_income": money(prof_at_readme_rate["net_income"]),
        "readme_consistent_net": money(abs(consistent_net_1)),
        "portfolio_roaa_reported": "{:.2%}".format(port["portfolio_roaa"]),
        "portfolio_roaa_consistent": "{:.2%}".format(
            consistent_total / port["total_balance"]
        ),
        "portfolio_overstatement": money(port["total_net_income"] - consistent_total),
        "portfolio_balance": money(port["total_balance"]),
        # --- the flat-registry collision -----------------------------------
        "admin_cost_mislabelled": render(
            "admin_cost", prof_at_readme_rate["admin_cost"]
        ),
        "cost_of_funds_mislabelled": render(
            "cost_of_funds", prof_at_readme_rate["cost_of_funds"]
        ),
    }
    figures["_sweep_unclamped"] = "{:,}".format(unclamped)
    figures["_sweep_false_negatives"] = "{:,}".format(false_negatives)
    return figures


# ---------------------------------------------------------------------------
# CHANGELOG parsing
# ---------------------------------------------------------------------------

#: Figures that quote a DEFECT rather than a computed result. The rates the
#: 0.1.0 README claimed were hand-transcribed and wrong; nothing in the code
#: produces them, which is precisely the entry's point. Every exemption must
#: still actually appear in the entry, so a stale one fails.
QUOTED_DEFECT_FIGURES = {
    "9.5775%": "recommended rate the hand-transcribed 0.1.0 README claimed",
    "8.0775%": "breakeven rate the hand-transcribed 0.1.0 README claimed",
}

FIGURE_RE = re.compile(r"-?\$[\d,]+(?:\.\d+)?|-?\d[\d,]*(?:\.\d+)?%")
#: A code span whose entire body is a figure is a claim (the rendering table
#: quotes its figures that way). Any other code span is an identifier or a
#: format spec — ``:.4%`` is not a measurement — and is dropped before scanning.
FIGURE_ONLY_RE = re.compile(r"-?\$?[\d,]+(?:\.\d+)?%?")


def changelog_text():
    with io.open(CHANGELOG, encoding="utf-8") as fh:
        return fh.read()


def current_entry(text=None):
    """Return the section for ``cdfipricing.__version__``. Derived from the
    running package's version, never typed."""
    text = changelog_text() if text is None else text
    heading = "## [%s]" % cdfipricing.__version__
    assert heading in text, "no CHANGELOG entry for %s" % cdfipricing.__version__
    body = text.split(heading, 1)[1]
    nxt = re.search(r"^## \[", body, re.M)
    return body[: nxt.start()] if nxt else body


def claim_text(section):
    """Drop inline code spans that are not themselves figures."""

    def repl(m):
        body = m.group(1)
        return body if FIGURE_ONLY_RE.fullmatch(body) else " "

    return re.sub(r"`([^`]*)`", repl, section)


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


@needs_sources
class TestChangelogQuantitativeClaims:
    def test_the_sweep_grid_size_and_count_are_quoted_correctly(self):
        """The specific claim that shipped fabricated: '48 of 3,200 (1.5%)'."""
        fig = derived_figures()
        section = current_entry()
        for key in ("_sweep_unclamped", "_sweep_false_negatives", "sweep_false_share"):
            assert fig[key] in section, (
                "CHANGELOG does not quote the measured %s (%r). Re-run the "
                "sweep; do not hand-edit." % (key, fig[key])
            )

    def test_the_grid_size_is_the_product_of_the_declared_constants(self):
        """Arithmetic the fabricated figure failed: the grid cannot be 3,200."""
        ltvs = {t["max_ltv"] for t in RISK_TIER_THRESHOLDS.values()}
        dscrs = {t["min_dscr"] for t in RISK_TIER_THRESHOLDS.values()}
        scores = {t["min_credit_score"] for t in RISK_TIER_THRESHOLDS.values()}
        expected = (
            len(SECTOR_DEFAULT_RATES)
            * len(DISTRESS_RISK_PREMIUMS)
            * len(ltvs)
            * len(dscrs)
            * len(scores)
        )
        _, _, cs = quickstart_inputs()
        unclamped, _ = sweep_counts(cs)
        assert unclamped == expected, (
            "every grid point is unclamped under the quickstart cost "
            "structure, so the two must agree: %d vs %d" % (unclamped, expected)
        )

    def test_the_sweep_result_is_invariant_to_loan_amount(self):
        """The CHANGELOG presents the count as a property of the grid, not of
        one loan size. Check that before quoting it as one."""
        _, _, cs = quickstart_inputs()
        counts = {amt: sweep_counts(cs, amt) for amt in (100_000, 750_000, 1_500_000)}
        assert len(set(counts.values())) == 1, (
            "the sweep result depends on loan_amount, so the CHANGELOG must "
            "not state it as a property of the grid: %r" % counts
        )
        assert next(iter(counts.values()))[1] > 0, (
            "no false negatives to count; the gates above would be vacuous"
        )

    def test_every_derived_figure_is_quoted(self):
        """Each computed figure must actually appear. Catches a figure that
        was corrected in one place and left stale in another."""
        fig = derived_figures()
        section = current_entry()
        missing = sorted(k for k, v in fig.items() if v not in section)
        assert not missing, (
            "figures derived from the code but absent from the CHANGELOG "
            "entry: %r" % {k: fig[k] for k in missing}
        )

    def test_no_unverified_figure_appears_in_the_entry(self):
        """The completeness gate. Every dollar amount and percentage in the
        entry must be one the code produced, or a listed quoted defect."""
        fig = derived_figures()
        allowed = set(fig.values()) | set(QUOTED_DEFECT_FIGURES)
        found = set(FIGURE_RE.findall(claim_text(current_entry())))
        assert len(found) > 10, "too few figures found; the scan is broken"
        stray = sorted(found - allowed)
        assert not stray, (
            "quantitative claims in the CHANGELOG entry that nothing in this "
            "module derives: %r. Derive them in derived_figures() or remove "
            "them — do not hand-type a measurement." % stray
        )

    def test_no_dead_quoted_defect_exemptions(self):
        section = current_entry()
        dead = sorted(f for f in QUOTED_DEFECT_FIGURES if f not in section)
        assert not dead, (
            "exempted figures that no longer appear in the entry: %r" % dead
        )
