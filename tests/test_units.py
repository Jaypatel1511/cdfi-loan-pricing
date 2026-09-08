"""Gates on the RENDERED summary, not on the underlying values.

The 0.1.0 defect was invisible to a value-level test: every number in
``PricingResult.profitability_metrics`` was correct. Only the rendering was
wrong — ``:.4%`` applied to dollar amounts, printing ``$73,687.50`` as
``7368750.0000%``. These gates therefore assert on the formatted strings.

Every field set here is DERIVED at test time from a live ``PricingResult``.
No field name and no count is typed as a literal.
"""

import pytest

from cdfipricing import LoanRequest, CDFICostStructure, recommend_rate
from cdfipricing.data.units import (
    UNIT_REGISTRY,
    Unit,
    UndeclaredUnitError,
    render,
    tagged,
)


@pytest.fixture
def result(standard_loan, standard_cost_structure):
    return recommend_rate(standard_loan, standard_cost_structure)


def _fields_with_unit(rendered, unit):
    """Derive the set of rendered fields declared as ``unit``."""
    return {n for n in rendered if UNIT_REGISTRY.get(n) is unit}


class TestUnitDeclarationCoverage:
    def test_every_rendered_field_has_a_declared_unit(self, result):
        rendered = result.rendered_fields()
        undeclared = sorted(n for n in rendered if n not in UNIT_REGISTRY)
        assert not undeclared, (
            "these rendered fields have no declared unit: %r; "
            "add them to cdfipricing.data.units.UNIT_REGISTRY" % undeclared
        )

    def test_registry_matches_pricing_result_exactly(self, result):
        """No dead declarations, no undeclared fields.

        If UNIT_REGISTRY is ever widened to cover fields produced outside
        PricingResult (e.g. loan_profitability), this gate must be widened to
        derive those field sets too rather than being loosened.
        """
        assert set(UNIT_REGISTRY) == set(result.rendered_fields())

    def test_field_set_is_not_empty(self, result):
        """Guard against the gates below passing vacuously."""
        assert len(result.rendered_fields()) > 5


class TestRenderedUnitsAreCorrect:
    def test_no_currency_field_renders_as_a_percentage(self, result):
        rendered = result.rendered_fields()
        currency = _fields_with_unit(rendered, Unit.CURRENCY)
        assert currency, "no CURRENCY fields discovered; gate would be vacuous"
        offenders = {n: rendered[n] for n in currency if "%" in rendered[n]}
        assert not offenders, "currency fields rendered with '%%': %r" % offenders

    def test_every_currency_field_renders_with_a_dollar_sign(self, result):
        rendered = result.rendered_fields()
        currency = _fields_with_unit(rendered, Unit.CURRENCY)
        assert currency
        missing = {n: rendered[n] for n in currency if "$" not in rendered[n]}
        assert not missing, "currency fields rendered without '$': %r" % missing

    def test_no_percent_field_renders_as_currency(self, result):
        rendered = result.rendered_fields()
        percents = _fields_with_unit(rendered, Unit.PERCENT)
        assert percents, "no PERCENT fields discovered; gate would be vacuous"
        offenders = {n: rendered[n] for n in percents if "$" in rendered[n]}
        assert not offenders, "percent fields rendered with '$': %r" % offenders

    def test_every_percent_field_renders_with_a_percent_sign(self, result):
        rendered = result.rendered_fields()
        percents = _fields_with_unit(rendered, Unit.PERCENT)
        assert percents
        missing = {n: rendered[n] for n in percents if "%" not in rendered[n]}
        assert not missing, "percent fields rendered without '%%': %r" % missing

    def test_boolean_fields_render_bare(self, result):
        rendered = result.rendered_fields()
        booleans = _fields_with_unit(rendered, Unit.BOOLEAN)
        assert booleans, "no BOOLEAN fields discovered; gate would be vacuous"
        for name in booleans:
            assert rendered[name] in ("True", "False"), (name, rendered[name])


class TestDeclarationsMatchIndependentGroundTruth:
    """The declared unit itself must be checkable, not just self-consistent.

    Every gate above derives its field set FROM ``UNIT_REGISTRY``, so a field
    declared under the wrong unit renders "correctly" for its (wrong)
    declaration and slips through. This class derives the truth from the
    model's own behaviour instead: a dollar amount scales linearly with
    ``loan_amount``; a rate, a ratio and a flag do not.
    """

    @staticmethod
    def _metrics(loan_amount, standard_loan, standard_cost_structure):
        import dataclasses

        loan = dataclasses.replace(standard_loan, loan_amount=loan_amount)
        result = recommend_rate(loan, standard_cost_structure)
        merged = dict(result.components_dict)
        merged.update(result.profitability_metrics)
        for name in result.HEADLINE_FIELDS:
            merged[name] = getattr(result, name)
        return merged

    def test_currency_declarations_match_fields_that_scale_with_loan_amount(
        self, standard_loan, standard_cost_structure
    ):
        base = self._metrics(750_000.0, standard_loan, standard_cost_structure)
        doubled = self._metrics(1_500_000.0, standard_loan, standard_cost_structure)
        assert set(base) == set(doubled)

        scales = set()
        invariant = set()
        for name, value in base.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            other = doubled[name]
            if value == 0:
                continue  # cannot tell a zero dollar amount from a zero rate
            if other == pytest.approx(value * 2.0):
                scales.add(name)
            elif other == pytest.approx(value):
                invariant.add(name)

        declared_currency = {
            n for n in base if UNIT_REGISTRY.get(n) is Unit.CURRENCY
        }
        assert scales, "no field scaled with loan_amount; gate would be vacuous"
        assert invariant, "no field was invariant; gate would be vacuous"
        assert scales == declared_currency, (
            "fields that scale with loan_amount are dollar amounts. "
            "scaling=%r declared CURRENCY=%r"
            % (sorted(scales), sorted(declared_currency))
        )
        mislabelled = invariant & declared_currency
        assert not mislabelled, (
            "declared CURRENCY but invariant to loan_amount: %r"
            % sorted(mislabelled)
        )

    def test_boolean_declarations_match_actual_bools(
        self, standard_loan, standard_cost_structure
    ):
        base = self._metrics(750_000.0, standard_loan, standard_cost_structure)
        actual_bools = {n for n, v in base.items() if isinstance(v, bool)}
        declared_bools = {n for n in base if UNIT_REGISTRY.get(n) is Unit.BOOLEAN}
        assert actual_bools, "no bool metrics found; gate would be vacuous"
        assert actual_bools == declared_bools, (
            "bool metrics=%r declared BOOLEAN=%r"
            % (sorted(actual_bools), sorted(declared_bools))
        )


class TestSummaryUsesTheDeclaredRendering:
    def test_summary_contains_every_rendered_field(self, result):
        """Every field's declared rendering must actually appear in summary().

        This is what ties the unit gates above to the string a user sees: a
        renderer that ignored the unit contract would pass the gates and fail
        here.
        """
        summary = result.summary()
        # Headline fields are labelled in prose ("Recommended rate"), the rest
        # are labelled by their field name. Both sets are derived, not typed.
        headline = set(result.HEADLINE_FIELDS)
        for name, shown in result.rendered_fields().items():
            if name not in headline:
                assert name in summary, "field %r missing from summary()" % name
            assert shown in summary, (
                "field %r renders as %r but that string is absent from "
                "summary()" % (name, shown)
            )

    def test_headline_fields_are_a_subset_of_the_rendered_fields(self, result):
        assert set(result.HEADLINE_FIELDS) <= set(result.rendered_fields())

    def test_currency_amounts_are_not_scaled_by_100(self, result, standard_loan):
        """The 0.1.0 symptom: correct value, 100x-inflated rendering."""
        rendered = result.rendered_fields()
        expected = result.recommended_rate * standard_loan.loan_amount
        assert result.profitability_metrics["annual_gross_income"] == pytest.approx(
            expected
        )
        assert rendered["annual_gross_income"] == "${:,.2f}".format(expected)
        assert "%" not in rendered["annual_gross_income"]


class TestUnitEnforcementAtProductionTime:
    def test_tagged_rejects_an_undeclared_field(self):
        with pytest.raises(UndeclaredUnitError):
            tagged([("cost_of_funds", 0.02), ("not_a_declared_metric", 1.0)])

    def test_tagged_accepts_declared_fields(self):
        assert tagged([("cost_of_funds", 0.02)]) == {"cost_of_funds": 0.02}

    def test_render_of_unknown_field_emits_no_unit_marker(self):
        shown = render("definitely_not_declared", 1234.5)
        assert "%" not in shown and "$" not in shown

    def test_every_unit_member_has_a_rendering(self):
        """Adding a Unit member without a rendering branch must not fall
        through to a percent/currency marker."""
        for unit in Unit:
            probe = True if unit is Unit.BOOLEAN else (3 if unit is Unit.COUNT else 0.25)
            from cdfipricing.data.units import _render_declared

            shown = _render_declared(probe, unit)
            assert shown, unit
            if unit is Unit.PERCENT:
                assert shown.endswith("%")
            elif unit is Unit.CURRENCY:
                assert shown.startswith("$")
            else:
                assert "%" not in shown and "$" not in shown
