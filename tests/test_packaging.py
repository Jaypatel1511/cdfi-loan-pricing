"""Gates on the files that decide what actually ships.

Two defects motivated this module, both invisible to every other test:

* ``setup.py`` declared nine trove classifiers and the built wheel's METADATA
  carried zero ``Classifier:`` lines. ``[project]`` in ``pyproject.toml`` owns
  the metadata, so setuptools ignored them. A CHANGELOG entry claimed the
  classifiers had been added; the artifact never saw them.
* ``MANIFEST.in`` had ``include LICENSE`` and no LICENSE file existed — an
  MIT-declared package shipping no license text, on this branch or on main.

The wheel's own METADATA is checked in CI (the ``build`` job), which already
builds a wheel; these gates hold the source invariants that make that check
pass, without making the unit suite depend on a build toolchain.
"""

import io
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYPROJECT = os.path.join(REPO_ROOT, "pyproject.toml")
SETUP_PY = os.path.join(REPO_ROOT, "setup.py")
MANIFEST = os.path.join(REPO_ROOT, "MANIFEST.in")

needs_sources = pytest.mark.skipif(
    not os.path.exists(PYPROJECT),
    reason="packaging files not present (installed-package layout)",
)


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _classifier_lines(text):
    """Every ``"... :: ..."`` trove string in a file, wherever it appears."""
    return re.findall(r'"([^"\n]+ :: [^"\n]+)"', text)


@needs_sources
class TestClassifiersHaveExactlyOneSource:
    def test_pyproject_declares_them(self):
        found = _classifier_lines(_read(PYPROJECT))
        assert found, (
            "pyproject.toml declares no trove classifiers. [project] owns the "
            "metadata, so declaring them anywhere else has no effect on the "
            "built distribution."
        )

    def test_setup_py_declares_none(self):
        found = _classifier_lines(_read(SETUP_PY))
        assert not found, (
            "setup.py declares classifiers %r. setuptools ignores them "
            "because [project] in pyproject.toml owns the metadata; a second "
            "copy here is dead and will drift." % found
        )

    def test_the_license_and_python_versions_are_declared(self):
        """Derived from requires-python, not typed: every minor version the
        package claims to support needs its own classifier."""
        text = _read(PYPROJECT)
        found = set(_classifier_lines(text))
        assert any(c.startswith("License :: ") for c in found), sorted(found)

        m = re.search(r'requires-python\s*=\s*">=3\.(\d+)"', text)
        assert m, "could not read requires-python from pyproject.toml"
        floor = int(m.group(1))
        declared = {
            int(c.rsplit(".", 1)[1])
            for c in found
            if c.startswith("Programming Language :: Python :: 3.")
        }
        assert declared, "no per-minor-version Python classifiers"
        assert min(declared) == floor, (
            "requires-python floor is 3.%d but the lowest declared Python "
            "classifier is 3.%d" % (floor, min(declared))
        )
        assert declared == set(range(floor, max(declared) + 1)), (
            "gap in the declared Python minor versions: %r" % sorted(declared)
        )


@needs_sources
class TestEveryManifestIncludeExists:
    def test_no_manifest_include_names_a_missing_file(self):
        """``include LICENSE`` with no LICENSE is silent: sdists are built
        without error and simply omit it."""
        missing = []
        for line in _read(MANIFEST).splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] == "include":
                if not os.path.exists(os.path.join(REPO_ROOT, parts[1])):
                    missing.append(parts[1])
        assert not missing, (
            "MANIFEST.in includes files that do not exist: %r" % missing
        )

    def test_the_scan_found_something_to_check(self):
        includes = [
            ln for ln in _read(MANIFEST).splitlines() if ln.startswith("include ")
        ]
        assert includes, "no plain include lines; gate above would be vacuous"

    def test_a_license_file_ships(self):
        path = os.path.join(REPO_ROOT, "LICENSE")
        assert os.path.exists(path), "package declares a license but ships no text"
        text = _read(path)
        assert "MIT" in text, "LICENSE does not match the declared MIT license"
        assert "Copyright" in text and re.search(r"Copyright \(c\) \d{4}", text), (
            "LICENSE has no copyright line"
        )
