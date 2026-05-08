from setuptools import setup, find_packages

setup(
    name="cdfi-loan-pricing",
    version="0.1.0",
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
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
    ],
)
