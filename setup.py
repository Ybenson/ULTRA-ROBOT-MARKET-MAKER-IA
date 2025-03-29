#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'installation pour ULTRA-ROBOT MARKET MAKER IA.

Ce script permet d'installer facilement le bot et ses dépendances.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ultra-robot-market-maker",
    version="1.0.0",
    author="Ybenson",
    author_email="admin@vitademy.com",
    description="Bot de market making ultra-puissant optimisé par IA",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ybenson/ULTRA-ROBOT-MARKET-MAKER-IA",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.19.0",
        "pandas>=1.1.0",
        "ccxt>=2.0.0",
        "websocket-client>=1.0.0",
        "aiohttp>=3.7.0",
        "python-dotenv>=0.15.0",
        "pyyaml>=5.4.0",
        "loguru>=0.5.0",
        "dash>=2.0.0",
        "plotly>=5.0.0",
        "tensorflow>=2.4.0; platform_system!='Windows' or python_version<'3.10'",
        "scikit-learn>=0.24.0",
        "statsmodels>=0.12.0",
        "redis>=4.0.0",
        "clickhouse-driver>=0.2.0",
        "psycopg2-binary>=2.9.0",
        "requests>=2.25.0",
        "apscheduler>=3.7.0",
        "cryptography>=3.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
            "black>=21.5b2",
            "isort>=5.9.0",
            "flake8>=3.9.0",
            "mypy>=0.812",
        ],
        "backtest": [
            "backtrader>=1.9.76.123",
            "pyfolio>=0.9.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "ultra-robot=src.init:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
