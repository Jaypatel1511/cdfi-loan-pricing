"""Gates on the RENDERED summary, not on the underlying values.

The 0.1.0 defect was invisible to a value-level test: every number in
``PricingResult.profitability_metrics`` was correct. Only the rendering was
wrong — ``:.4%`` applied to dollar amounts, printing ``$73,687.50`` as
``7368750.0000%``. These gates therefore assert on the formatted strings.

Every field set here is DERIVED at test time from a live ``PricingResult``.
No field name and no count is typed as a literal.
"""

import pytest

import cdfipricing

from cdfipricing import (
    LoanRequest,
    CDFICostStructure,
    recommend_rate,
    loan_profitability,
    portfolio_profitability,
    cross_subsidy_analysis,
    market_rate_comparison,
    compare_pricing_scenarios,
    sensitivity_analysis,
    cdfi_standard_scenarios,
)
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


def parse_summary(result):
    """Parse ``summary()`` back into ``{field name: rendered string}``.

    ``summary()`` has two blocks. The headline block labels its values in
    prose (``  Recommended rate : 9.8250%``) and is matched positionally
    against ``HEADLINE_FIELDS``; every other rendered line is
    ``  <field name><padding><rendered value>`` and is matched by name.
    Neither the prose labels nor the field names are typed here.

    A line the parser cannot attribute is dropped, which can only ever make
    the parsed mapping SMALLER than ``rendered_fields()`` — the comparison
    below is dict equality, so a dropped line fails the gate rather than
    passing it.
    """
    lines = result.summary().splitlines()
    headline = list(result.HEADLINE_FIELDS)

    labelled = [ln for ln in lines if " : " in ln]
    assert len(labelled) == len(headline), (
        "expected %d prose-labelled headline lines, found %d: %r"
        % (len(headline), len(labelled), labelled)
    )
    parsed = {
        name: labelled[i].split(" : ", 1)[1].strip()
        for i, name in enumerate(headline)
    }

    for line in lines:
        if " : " in line or not line.startswith("  "):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        assert parts[0] not in parsed, "duplicate field line in summary(): %r" % line
        parsed[parts[0]] = parts[1]
    return parsed


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
    model's own behaviour instead.

    Two units have a direct discriminator: a CURRENCY amount scales linearly
    with ``loan_amount`` (a rate does not), and a BOOLEAN is an actual
    ``bool``. PERCENT has no direct discriminator of its own — nothing in the
    model's behaviour separates a rate from a dimensionless ratio, since both
    are non-bool numerics invariant to ``loan_amount``. PERCENT is therefore
    resolved BY ELIMINATION, which is sound only while it is the one declared
    unit left after CURRENCY and BOOLEAN are removed.
    ``test_declared_units_are_exactly_the_ones_ground_truth_can_resolve``
    holds that precondition, and ``TestUnitEnumHasNoDeadMembers`` stops a
    fourth unit from being added at all. Weaken either and this class stops
    being able to catch a PERCENT field redeclared as something else.
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

    def test_declared_units_are_exactly_the_ones_ground_truth_can_resolve(
        self, result
    ):
        """Precondition for resolving PERCENT by elimination.

        CURRENCY and BOOLEAN are resolved directly. Any additional numeric
        unit — RATIO, COUNT, anything future — is indistinguishable from
        PERCENT by observing the model, so the moment one is declared the
        elimination below stops proving anything. Fail here instead of
        letting it pass silently.
        """
        declared = {UNIT_REGISTRY[n] for n in result.rendered_fields()}
        assert declared == {Unit.PERCENT, Unit.CURRENCY, Unit.BOOLEAN}, (
            "ground truth resolves CURRENCY directly, BOOLEAN directly and "
            "PERCENT only by elimination. Units in use: %r. Adding another "
            "numeric unit requires giving it a real discriminator here first."
            % sorted(u.name for u in declared)
        )

    def test_percent_declarations_match_what_is_left_after_currency_and_bools(
        self, standard_loan, standard_cost_structure
    ):
        """PERCENT by elimination: numeric, not a bool, invariant to
        ``loan_amount``.

        Redeclaring a rate as any other unit — the mutation the CURRENCY and
        BOOLEAN gates above both miss — lands the field in ``rate_like``
        without landing it in ``declared_percent``, and fails here.
        """
        base = self._metrics(750_000.0, standard_loan, standard_cost_structure)
        doubled = self._metrics(1_500_000.0, standard_loan, standard_cost_structure)
        assert set(base) == set(doubled)

        rate_like = set()
        for name, value in base.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if value == 0:
                continue  # a zero rate and a zero dollar amount look alike
            if doubled[name] == pytest.approx(value):
                rate_like.add(name)

        declared_percent = {n for n in base if UNIT_REGISTRY.get(n) is Unit.PERCENT}
        assert rate_like, "no rate-like field found; gate would be vacuous"
        assert rate_like == declared_percent, (
            "non-bool numerics invariant to loan_amount are rates. "
            "rate-like=%r declared PERCENT=%r"
            % (sorted(rate_like), sorted(declared_percent))
        )


class TestSummaryUsesTheDeclaredRendering:
    """``summary()`` must be built from ``render()``, field by field.

    The gate this replaced asserted only ``rendered_string in summary`` —
    plain substring containment. That is far weaker than it looks, because
    two fields can share a rendering: ``estimated_roaa`` and
    ``spread_over_breakeven`` are the same number under two names, so
    ``"1.2500%" in summary`` stayed true no matter what the line for
    ``estimated_roaa`` actually said. A renderer that ignored the unit
    contract entirely and printed a bare ``0.0125`` passed the whole module.

    These gates parse ``summary()`` back into ``{field: shown}`` and compare
    it to ``rendered_fields()`` for equality, so every field is checked
    against its OWN line.
    """

    def test_summary_renders_each_field_exactly_as_declared(self, result):
        parsed = parse_summary(result)
        expected = result.rendered_fields()
        assert len(expected) > 5, "gate would be near-vacuous"
        assert parsed == expected, (
            "summary() does not render every field through render(). "
            "in summary but wrong/absent in rendered_fields: %r"
            % {
                k: (parsed.get(k), expected.get(k))
                for k in set(parsed) | set(expected)
                if parsed.get(k) != expected.get(k)
            }
        )

    def test_summary_line_for_a_duplicated_value_is_checked_individually(
        self, result
    ):
        """The specific hole the containment gate had.

        ``estimated_roaa`` and ``spread_over_breakeven`` carry the same
        number, so containment could never distinguish them. Assert that
        both names are present as their own keys with their own renderings —
        derived by finding the duplicate-valued names, not by typing them.
        """
        expected = result.rendered_fields()
        by_rendering = {}
        for name, shown in expected.items():
            by_rendering.setdefault(shown, []).append(name)
        duplicated = [ns for ns in by_rendering.values() if len(ns) > 1]
        assert duplicated, (
            "no two fields share a rendering, so this gate is vacuous; if the "
            "duplicate-value known issue is ever fixed, delete this test"
        )
        parsed = parse_summary(result)
        for names in duplicated:
            for name in names:
                assert name in parsed, "field %r has no line of its own" % name
                assert parsed[name] == expected[name]

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
        """Adding a Unit member without a rendering branch must raise, not
        fall through to some other unit's marker."""
        from cdfipricing.data.units import _render_declared

        for unit in Unit:
            probe = True if unit is Unit.BOOLEAN else 0.25
            shown = _render_declared(probe, unit)
            assert shown, unit
            if unit is Unit.PERCENT:
                assert shown.endswith("%")
            elif unit is Unit.CURRENCY:
                assert shown.startswith("$")
            else:
                assert "%" not in shown and "$" not in shown


class TestUnitEnumHasNoDeadMembers:
    """``test_registry_matches_pricing_result_exactly`` forbids a registry
    entry no field uses, but said nothing about a ``Unit`` member no registry
    entry uses. 0.2.0 was about to ship ``RATIO`` and ``COUNT``: declared,
    documented, rendered — and reachable by nothing, so no gate in this file
    could ever have exercised them.

    A dead member is not merely unused here: it silently breaks the
    elimination argument in ``TestDeclarationsMatchIndependentGroundTruth``
    the moment anyone declares a field with it.
    """

    def test_every_unit_member_is_used_by_the_registry(self):
        used = set(UNIT_REGISTRY.values())
        dead = [u.name for u in Unit if u not in used]
        assert not dead, (
            "Unit members declared by no field: %r. Either declare a field "
            "with each (and give it a discriminator in "
            "TestDeclarationsMatchIndependentGroundTruth) or delete it." % dead
        )

    def test_the_registry_is_not_empty(self):
        assert UNIT_REGISTRY, "gate above would be vacuous"


class TestRegistryScopeIsExactlyPricingResult:
    """UNIT_REGISTRY is a flat ``name -> unit`` map, not ``(structure, name)``.

    The package reuses field names across structures with DIFFERENT units, so
    the registry's declarations are only true of ``PricingResult``.
    ``loan_profitability`` returns ``admin_cost`` and ``cost_of_funds`` as
    DOLLAR amounts under names this registry declares PERCENT. Nothing in the
    package renders those dicts, but ``render`` is public and a caller can.

    These gates measure the collision instead of assuming it away, across ALL
    SIX public dict-returning functions — an earlier version walked four of
    them, and the scope statements were written from that partial set. The
    first gate below also checks that the walk still covers every exported
    dict-returning function, so the scope statements in ``units.py``, the
    README and the CHANGELOG cannot quietly become claims about a subset.
    """

    #: Names shared between UNIT_REGISTRY and the six analysis dicts. Must
    #: stay in step with the Known-issues entry in CHANGELOG.md and the SCOPE
    #: section of cdfipricing/data/units.py.
    EXPECTED_COLLISIONS = {
        "admin_cost",  # dollars in loan_profitability, PERCENT here
        "cost_of_funds",  # dollars in loan_profitability, PERCENT here
        "annual_loss_provision",  # dollars in both; declared CURRENCY, correct
        "breakeven_rate",  # a rate in both; declared PERCENT, correct
        "capital_charge",  # a rate in both; declared PERCENT, correct
        "expected_loss",  # a rate in both; declared PERCENT, correct
        "recommended_rate",  # a rate in both; declared PERCENT, correct
        "target_rate",  # a rate in both; declared PERCENT, correct
    }

    #: The subset that is actually MISLABELLED by ``render``. Only
    #: loan_profitability reaches it.
    EXPECTED_MISLABELLED = {"admin_cost", "cost_of_funds"}

    @staticmethod
    def _analysis_dicts(standard_loan, standard_cost_structure):
        """Every public dict-returning analysis function, flattened to
        ``label -> {field name: value}``.

        ``compare_pricing_scenarios`` and ``sensitivity_analysis`` return
        LISTS of dicts; each row becomes its own label, so the two gates
        below can index ``base``/``bigger`` by the same key.
        """
        other = LoanRequest(
            loan_amount=500_000,
            term_years=7,
            amortization_years=15,
            sector="affordable_housing",
            ltv=0.60,
            dscr_at_origination=1.40,
            borrower_credit_score=710,
            geographic_distress_level="low",
        )
        loans = [standard_loan, other]
        rates = [0.085, 0.065]
        cs = standard_cost_structure
        out = {
            "loan_profitability": loan_profitability(loans[0], cs, rates[0]),
            "portfolio_profitability": portfolio_profitability(loans, rates, cs),
            "cross_subsidy_analysis": cross_subsidy_analysis(loans, rates, cs),
            "market_rate_comparison": market_rate_comparison(loans[0], cs, 0.115),
        }
        for i, row in enumerate(
            compare_pricing_scenarios(loans[0], cdfi_standard_scenarios())
        ):
            out["compare_pricing_scenarios[%d]" % i] = row
        for i, row in enumerate(
            sensitivity_analysis(
                loans[0], cs, "cost_of_funds", [0.02, 0.03, 0.04, 0.05]
            )
        ):
            out["sensitivity_analysis[%d]" % i] = row
        return out

    def test_collision_set_is_exactly_what_is_documented(
        self, standard_loan, standard_cost_structure
    ):
        dicts = self._analysis_dicts(standard_loan, standard_cost_structure)

        # The walk must cover EVERY public function that returns metric
        # dicts. A collision set derived from four of six would be the same
        # defect class this gate exists to catch, so the expected list is
        # derived from the package's own exports rather than typed.
        import inspect
        import typing

        wanted = (
            typing.Dict[str, typing.Any],
            typing.List[typing.Dict[str, typing.Any]],
        )
        exported = {
            name
            for name in cdfipricing.__all__
            if inspect.isfunction(getattr(cdfipricing, name))
            and inspect.signature(getattr(cdfipricing, name)).return_annotation
            in wanted
        }
        walked = {k.split("[", 1)[0] for k in dicts}
        assert len(exported) > 4, "export scan found too little; it is broken"
        assert walked == exported, (
            "_analysis_dicts must walk every public dict-returning function. "
            "walked=%r exported=%r" % (sorted(walked), sorted(exported))
        )

        collisions = {
            name
            for d in dicts.values()
            for name in d
            if name in UNIT_REGISTRY
        }
        assert collisions == self.EXPECTED_COLLISIONS, (
            "the set of names UNIT_REGISTRY shares with the analysis dicts "
            "changed: %r. Update EXPECTED_COLLISIONS, the SCOPE section of "
            "cdfipricing/data/units.py, and the CHANGELOG Known-issues entry "
            "together." % sorted(collisions)
        )

    def test_the_mislabelled_subset_is_exactly_what_is_documented(
        self, standard_loan, standard_cost_structure
    ):
        """Derived, not asserted: a collision is mislabelled when the value in
        the analysis dict scales with ``loan_amount`` (a dollar amount) while
        the registry declares it PERCENT."""
        import dataclasses

        base = self._analysis_dicts(standard_loan, standard_cost_structure)
        bigger = self._analysis_dicts(
            dataclasses.replace(
                standard_loan, loan_amount=standard_loan.loan_amount * 2
            ),
            standard_cost_structure,
        )
        mislabelled = set()
        for key, d in base.items():
            for name, value in d.items():
                if name not in UNIT_REGISTRY or isinstance(value, bool):
                    continue
                if not isinstance(value, (int, float)) or value == 0:
                    continue
                if bigger[key].get(name) != pytest.approx(value * 2.0):
                    continue  # invariant to loan_amount => a rate
                if UNIT_REGISTRY[name] is not Unit.CURRENCY:
                    mislabelled.add(name)
        assert mislabelled == self.EXPECTED_MISLABELLED, (
            "dollar amounts in the analysis dicts carrying a non-CURRENCY "
            "declaration: %r" % sorted(mislabelled)
        )

    def test_render_actually_mislabels_them(
        self, standard_loan, standard_cost_structure
    ):
        """The scope warning is not hypothetical. Keep it demonstrated."""
        prof = self._analysis_dicts(standard_loan, standard_cost_structure)[
            "loan_profitability"
        ]
        for name in sorted(self.EXPECTED_MISLABELLED):
            assert prof[name] > 100.0, (name, prof[name])  # unmistakably dollars
            assert render(name, prof[name]).endswith("%"), name
