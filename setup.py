#!/usr/bin/env python3
"""CachePIM setup script for legacy setuptools compatibility."""

from setuptools import find_packages, setup

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="cachepim",
    version="1.1.0",
    description="A Statistical Simulator for Cache-Aware CPU–Processing-in-Memory Execution",
    author="CachePIM Research Team",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cachepim = cachepim.run:main",
        ],
    },
)
