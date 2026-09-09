#!/usr/bin/env python3
"""Regenerate the README Quickstart section from examples/quickstart.py.

The README's Quickstart code and its printed output are both GENERATED. They
are never hand-transcribed: the code block is the source of
``examples/quickstart.py`` and the output block is that script's actual
captured stdout.

Usage::

    python3 scripts/gen_readme.py            # rewrite README.md in place
    python3 scripts/gen_readme.py --check    # exit 1 if README.md is stale

``tests/test_readme_quickstart.py`` runs the ``--check`` mode, so a change to
the pricing model that moves a printed figure turns the test suite red until
the README is regenerated.
"""

import argparse
import ast
import difflib
import io
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(REPO_ROOT, "README.md")
EXAMPLE = os.path.join(REPO_ROOT, "examples", "quickstart.py")

CODE_MARKER = "quickstart-code"
OUTPUT_MARKER = "quickstart-output"


def _begin(marker):
    return "<!-- BEGIN GENERATED: {} -->".format(marker)


def _end(marker):
    return "<!-- END GENERATED: {} -->".format(marker)


def example_source():
    """Return examples/quickstart.py source with its module docstring removed."""
    with io.open(EXAMPLE, encoding="utf-8") as fh:
        text = fh.read()
    tree = ast.parse(text)
    lines = text.splitlines()
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        start = tree.body[0].end_lineno  # 1-indexed, inclusive
        lines = lines[start:]
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines).rstrip("\n")


def example_output():
    """Run examples/quickstart.py and return its stdout verbatim."""
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONHASHSEED"] = "0"
    proc = subprocess.run(
        [sys.executable, EXAMPLE],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise SystemExit(
            "examples/quickstart.py failed (exit {}):\n{}".format(
                proc.returncode, proc.stderr.decode("utf-8", "replace")
            )
        )
    return proc.stdout.decode("utf-8").rstrip("\n")


def splice(text, marker, body):
    """Replace the content between ``marker``'s BEGIN/END comments."""
    begin, end = _begin(marker), _end(marker)
    if text.count(begin) != 1 or text.count(end) != 1:
        raise SystemExit(
            "README.md must contain exactly one {!r} and one {!r}".format(begin, end)
        )
    head, rest = text.split(begin, 1)
    _stale, tail = rest.split(end, 1)
    return "{}{}\n{}\n{}{}".format(head, begin, body, end, tail)


def build(current):
    out = splice(
        current, CODE_MARKER, "```python\n{}\n```".format(example_source())
    )
    out = splice(
        out, OUTPUT_MARKER, "```text\n{}\n```".format(example_output())
    )
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit 1 with a diff instead of rewriting README.md",
    )
    args = ap.parse_args(argv)

    with io.open(README, encoding="utf-8") as fh:
        current = fh.read()
    regenerated = build(current)

    if current == regenerated:
        if not args.check:
            print("README.md already up to date")
        return 0

    if args.check:
        diff = difflib.unified_diff(
            current.splitlines(True),
            regenerated.splitlines(True),
            fromfile="README.md (committed)",
            tofile="README.md (regenerated)",
        )
        sys.stdout.write("".join(diff))
        sys.stdout.write(
            "\nREADME.md is stale. Run: python3 scripts/gen_readme.py\n"
        )
        return 1

    with io.open(README, "w", encoding="utf-8") as fh:
        fh.write(regenerated)
    print("README.md regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
