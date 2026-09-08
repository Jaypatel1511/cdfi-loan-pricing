"""Per-field unit contract for every value the package renders.

The rendering defect fixed in 0.2.0 (dollar figures printed with a ``%``
suffix, inflated 100x) happened because a renderer inferred a unit from a
value's *Python type* — every ``float`` was formatted as a percentage. A
float carries no unit, so the only safe source of a unit is an explicit
declaration.

This module is that declaration. Two mechanisms keep it from drifting:

1. :func:`tagged` — the package builds every metric dict through it, so a
   metric added without a declared unit raises immediately rather than
   silently rendering wrong.
2. :func:`render` — falls back to a unit-free rendering for names it does
   not know, so an undeclared name can never be *mislabelled*. It can only
   be under-labelled.
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
    """The unit a rendered field is expressed in."""

    #: A rate or margin held as a decimal fraction; rendered ``9.8250%``.
    PERCENT = "percent"
    #: A dollar figure; rendered ``$73,687.50``.
    CURRENCY = "currency"
    #: A dimensionless multiple (DSCR, coverage ratio); rendered ``1.2500``.
    RATIO = "ratio"
    #: A true/false flag; rendered ``True`` / ``False``.
    BOOLEAN = "boolean"
    #: A whole-number tally; rendered ``3``.
    COUNT = "count"


class UndeclaredUnitError(KeyError):
    """Raised when the package produces a field with no declared unit."""


#: The single source of truth for field units. Every field the package
#: renders MUST appear here. Grouped by the structure that produces it.
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
    if unit is Unit.RATIO:
        return f"{value:.4f}"
    if unit is Unit.COUNT:
        return f"{value:,d}"
    return str(value)  # Unit.BOOLEAN


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
    still prints. Package-produced fields cannot reach this path: they are
    built through :func:`tagged`, which rejects undeclared names.
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
