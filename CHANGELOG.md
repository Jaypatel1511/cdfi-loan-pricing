# Changelog

All notable changes to `cdfi-loan-pricing` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-09-08

0.1.0 shipped with a rendering defect, a documentation defect, a validation
gap, a missing export, and one boolean that was computed wrongly.

Scope of the rendering defect, stated precisely and narrowly: **every value
in the `PricingResult` that 0.1.0's `recommend_rate` returned — the three
headline rates, all six rate components and all three dollar amounts — was
numerically correct**, with one exception, the `meets_target_roaa` flag,
which was genuinely wrong for some inputs (see below). Three of the dollar
amounts were *formatted* under the wrong unit by `PricingResult.summary()` —
a display bug only; the dict values behind them were right.

That statement is about `recommend_rate` and nothing else. It does **not**
extend to `loan_profitability` or `portfolio_profitability`, whose
`net_income`, `roaa`, `is_profitable` and `portfolio_roaa` are computed from
a different and internally inconsistent cost stack — they disagree with
`PricingResult` for the same loan at the same rate, in 0.1.0 and still in
0.2.0. That is described under Known issues, and this release does not touch
it.

So: anyone who read rates or dollars off `summary()` saw three fields
mislabelled; anyone who used `recommend_rate`'s returned floats directly was
unaffected except for that flag; anyone who used `loan_profitability`'s
`net_income` / `roaa` / `is_profitable` was and remains exposed to the
Known-issues defect.

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
  field the summary renders declares a unit (percent / currency / boolean) in
  `cdfipricing.data.units.UNIT_REGISTRY`, and the renderer reads that
  declaration. Metric dicts are now built through `units.tagged()`, which
  raises `UndeclaredUnitError` if a field is added without a declared unit.
  The unit gates parse `summary()` back apart and compare it to
  `PricingResult.rendered_fields()` field by field, so a renderer that
  ignored the contract fails them.

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

- **`meets_target_roaa` was False for loans that do meet the target.**
  `estimated_roaa` is computed as `recommended_rate - breakeven_rate`, and an
  unclamped recommended rate is `breakeven + target_roaa +
  risk_tier_premium`, so the difference equals `target_roaa` plus a
  non-negative premium — the flag is True by construction. IEEE-754 landed
  that subtraction about 7e-18 below `target_roaa`, and the bare `>=`
  comparison reported False. The sweep grid is the product of the package's
  own constants — 10 sectors x 4 distress levels x 4 LTV, 4 DSCR and 4
  credit-score thresholds — so it is 2,560 points, every one of them
  unclamped under this cost structure. **22 of those 2,560 inputs (0.86%)
  reported `meets_target_roaa: False` in error**, all of them tier_1 loans
  priced exactly at target; the count is unchanged across loan sizes from
  100k to 1.5M. The comparison now carries a tolerance. No rate and no dollar
  amount changes; only this flag does.

  A previous draft of this entry claimed 48 offenders on a 3,200-point grid.
  Nothing produced those numbers — 10 x 4 x 4 x 4 x 4 is not 3,200 — and no
  gate caught it, because the hand-typed-figure gate covered the README only.
  `tests/test_changelog_claims.py` now re-derives every dollar amount and
  percentage in this entry from the code and fails on any that it cannot.

### Added

- `risk_tier` and `risk_tier_premium` are now exported from `cdfipricing`.
  0.1.0 shipped a `risk_tier_premium` component in every pricing result and
  a README claim of "risk-tier classification", but neither function was
  reachable from the top-level package. `all_components` is exported too.
- `cdfipricing.data.units` — `Unit`, `UNIT_REGISTRY`, `unit_for`, `render`,
  `tagged`, `UndeclaredUnitError`. `Unit`, `UNIT_REGISTRY`, `unit_for` and
  `render` are re-exported from `cdfipricing`. `Unit` declares exactly the
  three units the registry uses (percent, currency, boolean); a member
  nothing declares is dead code that no gate can exercise, and one is now
  rejected by a test. That also keeps the independent ground-truth check
  sound: it resolves currency and boolean directly and percent by
  elimination, which only works while percent is the one unit left over.
- `LICENSE` — the MIT text `MANIFEST.in` had been including since 0.1.0
  without the file existing. `setup.py` and `pyproject.toml` both declared
  the package MIT-licensed and no license text shipped.
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
  export gates, a gate that the three version sites agree, a gate that the
  expected-loss DSCR ladder reads the risk-tier table, gates recording which
  functions the deferred net-income defect reaches, and
  `tests/test_changelog_claims.py` — which re-derives every quantitative
  claim in this entry.

### Changed

- `pyproject.toml` declares packages explicitly
  (`[tool.setuptools.packages.find] include = ["cdfipricing*"]`) so the new
  top-level `examples/` and `scripts/` directories cannot be picked up by
  flat-layout auto-discovery.
- **`pyproject.toml` now declares the trove classifiers, and `setup.py` no
  longer does.** `[project]` in `pyproject.toml` owns the metadata, so
  setuptools ignored `setup.py`'s classifier list entirely: the 0.2.0 wheel
  built before this change carried zero `Classifier:` lines in its METADATA,
  including the license and the Python-version classifiers. Declaring them in
  `setup.py` — as an earlier draft of this entry claimed to have done — has
  no effect on the artifact. There is now one source for them and a test that
  reads the built wheel's METADATA.
- The expected-loss DSCR ladder reads its breakpoints from
  `RISK_TIER_THRESHOLDS` instead of repeating them as literals. Editing the
  tier table used to move risk tiering while leaving expected loss on the old
  ladder, with nothing failing.

### Compatibility

`sector` validation is the only behaviour change that can turn working
0.1.0 code into an error: a `LoanRequest` built with a sector outside
`SECTOR_DEFAULT_RATES` now raises `ValueError` instead of being priced at a
2.00% default rate.

For every input that was valid in 0.1.0, every number this package computes —
across `recommend_rate`, `loan_profitability`, `portfolio_profitability`,
`cross_subsidy_analysis` and `market_rate_comparison` alike — is unchanged.
0.2.0 alters no arithmetic. The single value that changes is the
`meets_target_roaa` flag, which flips False to True on the 0.86% of
unclamped inputs where 0.1.0 was reporting a floating-point artifact.

### Known issues (present in 0.1.0, NOT fixed in 0.2.0)

- **`loan_profitability` can report a loan as profitable while the same
  returned dict says it is below breakeven.** `admin_cost_component` already
  nets fee income out of the admin cost (`admin_cost_pct - fee_income_pct`);
  `loan_profitability` then adds `fee_income_pct * loan_amount` again, and it
  omits the capital charge that `breakeven_rate` includes. On the README
  quickstart loan priced at its own recommended rate, the gap is exactly
  `fee_income_pct * amount + capital_charge * amount` = $3,750.00 +
  $5,062.50 = **$8,812.50** ($18,187.50 from `loan_profitability` vs
  $9,375.00 from `PricingResult.net_income_estimate`). `roaa` diverges by the
  same amount, not only `net_income`: 2.4250% from `loan_profitability`
  against 1.2500% from `PricingResult`.

  **The consequence is a flipped verdict, not just a different figure**, and
  both halves of it are printed in the README's own generated quickstart:

  - At the quickstart's 8.50%, `loan_profitability` returns
    `is_profitable: True` and `net_income: $8,250.00` while the *same dict*
    returns a negative `spread_to_breakeven` — the loan is $562.50 a year
    below breakeven.
  - `portfolio_profitability` reports `portfolio_roaa: 0.84%` for the
    quickstart portfolio where the breakeven-consistent figure is -0.33%, an
    overstatement of $14,687.50 on $1,250,000.00 of balances. Its
    `loans_below_breakeven` count is derived from the spread and is correct,
    so the two fields of one result disagree.

  **Which functions this reaches:** `loan_profitability`
  (`net_income`, `roaa`, `is_profitable`) and `portfolio_profitability`
  (`total_net_income`, `portfolio_roaa`). **`cross_subsidy_analysis` and
  `market_rate_comparison` are NOT affected** — an earlier draft of this
  entry named `cross_subsidy_analysis` and was wrong. Cross-subsidy derives
  every output from `spread_to_breakeven = actual_rate - breakeven_rate` and
  never reads `net_income`; `market_rate_comparison` never calls
  `loan_profitability` at all.
  `tests/test_profitability.py::TestWhichConsumersReadTheDeferredNetIncome`
  holds that split by poisoning `net_income` and checking which outputs move.

  Reconciling the two definitions changes computed pricing outputs and is a
  methodology decision, so it is deliberately deferred to a dedicated pass
  rather than folded into a rendering fix.

- **`UNIT_REGISTRY` is keyed by field name alone, so its declarations are
  true of `PricingResult` and of nothing else.** `loan_profitability`
  returns `admin_cost` and `cost_of_funds` as dollar amounts under names the
  registry declares percent, so `render("admin_cost", ...)` on that dict
  produces `1875000.0000%` and `render("cost_of_funds", ...)` produces
  `1912500.0000%`. The package never renders those dicts —
  `PricingResult.summary()` is the only renderer — but `render` is public.
  Do not point it at anything other than a `PricingResult`. A test derives
  the exact set of colliding names and fails if it grows; keying the registry
  by (structure, field) is the real fix and is not in this release.

- `estimated_roaa` and `spread_over_breakeven` are, by construction, always
  the same number under two names.

- `borrower_credit_score`, `target_roae` and `fee_income_pct` are not
  range-validated.

- The `Returns:` docstrings of `market_rate_comparison`,
  `portfolio_profitability` and `cross_subsidy_analysis` do not list every
  key those functions return.

## [0.1.0] — 2026-05-08

Initial release: component-driven CDFI loan pricing (cost of funds,
expected loss, admin cost, capital charge, target return, risk-tier
premium), breakeven and target rate, sensitivity analysis, pre-built CDFI
cost-structure scenarios, loan and portfolio profitability, cross-subsidy
analysis, and market-rate benchmarking.
