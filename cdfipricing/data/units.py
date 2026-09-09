"""Per-field unit contract for every value the package renders.

The rendering defect fixed in 0.2.0 (dollar figures printed with a ``%``
suffix, inflated 100x) happened because a renderer inferred a unit from a
value's *Python type* — every ``float`` was formatted as a percentage. A
float carries no unit, so the only safe source of a unit is an explicit
declaration.

This module is that declaration. Two mechanisms keep it from drifting:

1. :func:`tagged` — ``components_dict`` and ``profitability_metrics`` are
   built through it, so a metric added to either without a declared unit
   raises immediately rather than silently rendering wrong.
2. :func:`render` — falls back to a unit-free rendering for names it does
   not know, so a name that is *absent* from the registry can only be
   under-labelled, never mislabelled.

SCOPE — read this before calling :func:`render` yourself
--------------------------------------------------------

The registry covers exactly the fields of
:class:`~cdfipricing.data.schema.PricingResult`: the three headline rates,
the six rate components and the seven profitability metrics that
:func:`~cdfipricing.models.pricing.recommend_rate` returns. A gate in
``tests/test_units.py`` holds it to exactly that set.

It is a flat ``name -> unit`` map, so it carries no information about which
structure a name came from, and this package reuses names across structures
with *different* units. ``loan_profitability`` returns ``admin_cost`` and
``cost_of_funds`` as DOLLAR amounts, while this registry declares both names
PERCENT because they are rates in ``PricingResult.components_dict``:
``render("admin_cost", 18750.0)`` returns ``'1875000.0000%'``. The package
itself never does this — ``PricingResult.summary()`` is the only renderer,
and it only ever renders a ``PricingResult``.

The collision is narrower than "never point :func:`render` at an analysis
dict". Measured across all six public functions that return metric dicts —
``loan_profitability``, ``portfolio_profitability``,
``cross_subsidy_analysis``, ``market_rate_comparison``,
``compare_pricing_scenarios`` and ``sensitivity_analysis`` — eight names
collide with this registry and exactly TWO of them are mislabelled:
``admin_cost`` and ``cost_of_funds``, reached only through
``loan_profitability``, which holds them as dollars. The other six
(``annual_loss_provision``, ``breakeven_rate``, ``capital_charge``,
``expected_loss``, ``recommended_rate``, ``target_rate``) carry the same
unit in those dicts as here and render correctly.
``portfolio_profitability`` and ``cross_subsidy_analysis`` collide with
nothing at all. So: do not call :func:`render` on ``loan_profitability``'s
``admin_cost`` or ``cost_of_funds``; everything else in those six dicts is
either absent from the registry (and falls back unit-free) or declared
correctly.

``tests/test_units.py`` walks all six functions, derives both sets, and
fails if either changes. That gate also derives the list of six from
``cdfipricing.__all__`` (every export annotated ``Dict[str, Any]`` or
``List[Dict[str, Any]]``) and fails if the walk misses one, so this scope
claim cannot quietly become a claim about a subset.
"""

from enum import Enum
from typing import Any, Dict, Iterable, Sequence

__all__ = [
    "Unit",
    "UndeclaredUnitError",
    "UNIT_REGISTRY",
    "unit_for",
    "is_declared",
    "render",
    "tagged",
]


class Unit(Enum):
    """The unit a rendered field is expressed in.

    Only units that :data:`UNIT_REGISTRY` actually uses are defined. A
    member that nothing declares is dead code that cannot be exercised, so
    ``tests/test_units.py`` fails if one is added and left unused. That gate
    is load-bearing: the independent ground-truth check in that module
    resolves CURRENCY and BOOLEAN directly and every other declared unit by
    elimination, which is only sound while PERCENT is the sole remaining
    member.
    """

    #: A rate or margin held as a decimal fraction; rendered ``9.8250%``.
    PERCENT = "percent"
    #: A dollar figure; rendered ``$73,687.50``.
    CURRENCY = "currency"
    #: A true/false flag; rendered ``True`` / ``False``.
    BOOLEAN = "boolean"


class UndeclaredUnitError(KeyError):
    """Raised when the package produces a field with no declared unit."""


#: The single source of truth for the units of every field
#: :meth:`PricingResult.summary` renders. Grouped by the structure that
#: produces it. See this module's SCOPE section: these names are NOT
#: qualified by structure, and three of them are reused with a different
#: unit by ``cdfipricing.analysis.profitability``.
UNIT_REGISTRY: Dict[str, Unit] = {
    # --- PricingResult headline rates (schema.PricingResult.summary) ------
    "recommended_rate": Unit.PERCENT,
    "breakeven_rate": Unit.PERCENT,
    "target_rate": Unit.PERCENT,
    # --- PricingResult.components_dict (components.all_components) --------
    "cost_of_funds": Unit.PERCENT,
    "expected_loss": Unit.PERCENT,
    "admin_cost": Unit.PERCENT,
    "capital_charge": Unit.PERCENT,
    "target_return": Unit.PERCENT,
    "risk_tier_premium": Unit.PERCENT,
    # --- PricingResult.profitability_metrics (pricing.recommend_rate) -----
    # These four ARE rates and must keep their percent rendering.
    "net_interest_margin": Unit.PERCENT,
    "spread_over_breakeven": Unit.PERCENT,
    "estimated_roaa": Unit.PERCENT,
    # These three are DOLLARS. Rendering them as percentages was the 0.1.0
    # defect: the values were correct, the suffix and the 100x scaling
    # applied by ``:.4%`` were not.
    "annual_gross_income": Unit.CURRENCY,
    "annual_loss_provision": Unit.CURRENCY,
    "net_income_estimate": Unit.CURRENCY,
    # A bool, not a rate.
    "meets_target_roaa": Unit.BOOLEAN,
}


def is_declared(name: str) -> bool:
    """Return True if ``name`` has a declared unit."""
    return name in UNIT_REGISTRY


def unit_for(name: str) -> Unit:
    """Return the declared unit for ``name``.

    Raises:
        UndeclaredUnitError: If the field has no declared unit.
    """
    try:
        return UNIT_REGISTRY[name]
    except KeyError:
        raise UndeclaredUnitError(
            f"field {name!r} has no declared unit; add it to "
            f"cdfipricing.data.units.UNIT_REGISTRY"
        ) from None


def _render_declared(value: Any, unit: Unit) -> str:
    if unit is Unit.PERCENT:
        return f"{value:.4%}"
    if unit is Unit.CURRENCY:
        return f"${value:,.2f}"
    if unit is Unit.BOOLEAN:
        return str(value)
    # Reached only if a Unit member is added without a branch here. Raise
    # rather than falling through to some other unit's formatting.
    raise UndeclaredUnitError(f"no rendering branch for {unit!r}")


def _render_unitless(value: Any) -> str:
    """Render a value whose unit is unknown, emitting no unit marker."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render(name: str, value: Any) -> str:
    """Render ``value`` according to ``name``'s declared unit.

    A name with no declared unit is rendered without any unit marker (no
    ``%``, no ``$``) rather than raising, so that a caller-built
    :class:`~cdfipricing.data.schema.PricingResult` carrying custom keys
    still prints.

    That fallback is a safety net for *absent* names only. It does not make
    this function safe to point at an arbitrary dict:

    * Fields built through :func:`tagged` — every key of
      ``components_dict`` and ``profitability_metrics`` — are guaranteed
      declared, so they never take the fallback.
    * ``PricingResult.HEADLINE_FIELDS`` are *not* built through
      :func:`tagged`; they reach this function directly. They are declared
      today and a gate keeps them declared, but the guarantee is that gate,
      not :func:`tagged`.
    * Keys of ``loan_profitability`` and the other analysis dicts are not
      built through :func:`tagged` either. Most are absent from the registry
      and fall back correctly; ``admin_cost`` and ``cost_of_funds`` are
      present, hold dollars there, and are therefore rendered as
      percentages. See this module's SCOPE section.
    """
    if not is_declared(name):
        return _render_unitless(value)
    return _render_declared(value, unit_for(name))


def tagged(pairs: Iterable[Sequence[Any]]) -> Dict[str, Any]:
    """Build a metric dict from ``(name, value)`` pairs, enforcing units.

    Args:
        pairs: An iterable of ``(name, value)`` pairs, in render order.

    Returns:
        An insertion-ordered dict of the pairs.

    Raises:
        UndeclaredUnitError: If any name has no declared unit.
    """
    out: Dict[str, Any] = {}
    missing = []
    for pair in pairs:
        name, value = pair[0], pair[1]
        if not is_declared(name):
            missing.append(name)
        out[name] = value
    if missing:
        raise UndeclaredUnitError(
            f"no declared unit for {missing!r}; add to "
            f"cdfipricing.data.units.UNIT_REGISTRY"
        )
    return out
