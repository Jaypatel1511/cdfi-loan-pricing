"""Compatibility shim only.

``pyproject.toml``'s ``[project]`` table is the authority for this package's
metadata; setuptools silently ignores anything declared here for a field
listed there. Do NOT add metadata to this file expecting it to reach the
built distribution — a classifier list here produced a wheel whose METADATA
carried no ``Classifier:`` lines at all. ``version`` is duplicated on
purpose: ``tests/test_validation.py::TestVersionSitesAgree`` reads it as one
of the three version sites.
"""

from setuptools import setup, find_packages

setup(
    name="cdfi-loan-pricing",
    version="0.2.0",
    description="CDFI loan pricing model — cost of capital, target ROAA, expected loss, and admin cost analysis to compute minimum viable loan rate",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Jay Patel",
    author_email="thejaypatel1511@gmail.com",
    url="https://github.com/Jaypatel1511/cdfi-loan-pricing",
    license="MIT",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.9",
    install_requires=[],
)
