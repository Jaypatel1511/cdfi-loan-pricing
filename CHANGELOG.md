# Changelog

All notable changes to `cdfi-loan-pricing` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-09-08

0.1.0 shipped with two rendering/documentation defects and two gaps. **No
computed value was wrong in 0.1.0.** Every rate, dollar amount and component
returned by the library was correct; the defects were in how three of those
values were *formatted* by `PricingResult.summary()`, in figures quoted by
hand in the README, and in missing input validation and a missing export.
Anyone who read numbers off `summary()` saw three of them mislabelled;
anyone who used the returned floats directly was unaffected.

### Fixed

- **`PricingResult.summary()` printed dollar amounts as percentages,
  inflated 100x.** `summary()` inferred each metric's unit from its Python
  type and applied `:.4%` to every `float`. Measured on the README
  quickstart inputs, three of the seven profitability metrics were affected:

  | field | 0.1.0 rendering | correct rendering |
  | --- | --- | --- |
  | `annual_gross_income` | `7368750.0000%` | `$73,687.50` |
  | `annual_loss_provision` | `2137500.0000%` | `$21,375.00` |
  | `net_income_estimate` | `937500.0000%` | `$9,375.00` |

  The other four profitability metrics (`net_interest_margin`,
  `spread_over_breakeven`, `estimated_roaa`, `meets_target_roaa`) and all
  six rate components rendered correctly in 0.1.0 and are unchanged. The
  underlying dict values were correct in 0.1.0 and are unchanged.

  The fix is a per-field unit contract, not a per-loop format change: every
  field the summary renders declares a unit (percent / currency / ratio /
  boolean / count) in `cdfipricing.data.units.UNIT_REGISTRY`, and the
  renderer reads that declaration. Metric dicts are now built through
  `units.tagged()`, which raises `UndeclaredUnitError` if a field is added
  without a declared unit.

- **The README quickstart quoted rates the code does not produce.** The
  documented output claimed `Recommended rate : 9.5775%` and
  `Breakeven rate : 8.0775%`; the actual values for those inputs are
  **9.8250%** and **8.5750%**. The figures had been hand-transcribed. The
  README Quickstart code block and its output are now generated from
  `examples/quickstart.py` by `scripts/gen_readme.py`, and a test fails if
  they drift.

- **An unknown `sector` was accepted silently.** `expected_loss_component`
  looked the sector up with `SECTOR_DEFAULT_RATES.get(loan.sector, 0.0200)`.
  The 2.00% fallback is the same value as `small_business`, so
  `sector="zzz_not_a_sector"` produced output byte-identical to
  `sector="small_business"` — a typo priced a loan with no error and no
  warning. `LoanRequest` now raises `ValueError` for a sector outside
  `SECTOR_DEFAULT_RATES`, matching how it already handled an invalid
  `geographic_distress_level`, and the silent fallback in
  `expected_loss_component` has been removed.

### Added

- `risk_tier` and `risk_tier_premium` are now exported from `cdfipricing`.
  0.1.0 shipped a `risk_tier_premium` component in every pricing result and
  a README claim of "risk-tier classification", but neither function was
  reachable from the top-level package. `all_components` is exported too.
- `cdfipricing.data.units` — `Unit`, `UNIT_REGISTRY`, `unit_for`, `render`,
  `tagged`, `UndeclaredUnitError`. `Unit`, `UNIT_REGISTRY`, `unit_for` and
  `render` are re-exported from `cdfipricing`.
- `PricingResult.rendered_fields()` — the mapping of every field
  `summary()` renders to its rendered string, so callers (and tests) can
  inspect the rendering without parsing the summary text.
- `examples/quickstart.py` — the runnable source of the README quickstart.
- `scripts/gen_readme.py` — regenerates the README quickstart; `--check`
  mode fails on drift.
- Continuous integration (`.github/workflows/ci.yml`) on Python 3.9, 3.10,
  3.11 and 3.12, with action versions pinned to commit SHAs. 0.1.0 shipped
  with no CI at all.
- Tests: rendered-unit gates, README-drift gates, sector-validation gates,
  export gates, and a gate that the three version sites agree.

### Changed

- `pyproject.toml` declares packages explicitly
  (`[tool.setuptools.packages.find] include = ["cdfipricing*"]`) so the new
  top-level `examples/` and `scripts/` directories cannot be picked up by
  flat-layout auto-discovery.
- `setup.py` declares Python 3.10, 3.11 and 3.12 classifiers alongside 3.9.

### Compatibility

`sector` validation is the only behaviour change that can turn working
0.1.0 code into an error: a `LoanRequest` built with a sector outside
`SECTOR_DEFAULT_RATES` now raises `ValueError` instead of being priced at a
2.00% default rate. Rates, components and profitability values are
numerically unchanged for every input that was valid in 0.1.0.

## [0.1.0] — 2026-05-08

Initial release: component-driven CDFI loan pricing (cost of funds,
expected loss, admin cost, capital charge, target return, risk-tier
premium), breakeven and target rate, sensitivity analysis, pre-built CDFI
cost-structure scenarios, loan and portfolio profitability, cross-subsidy
analysis, and market-rate benchmarking.
