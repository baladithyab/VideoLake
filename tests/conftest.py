#!/usr/bin/env python3
"""
Pytest configuration for real AWS E2E tests.
"""

import pytest


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--real-aws",
        action="store_true",
        default=False,
        help="Enable real AWS tests (required to run these tests)"
    )


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "real_aws: mark test as using real AWS resources (will incur costs)"
    )
    config.addinivalue_line(
        "markers", "expensive: mark test as expensive (e.g., OpenSearch domain)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (takes >1 minute)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests unless --real-aws flag is provided."""
    if not config.getoption("--real-aws"):
        skip_real_aws = pytest.mark.skip(
            reason="Real AWS tests require --real-aws flag (will incur costs!)"
        )
        for item in items:
            if "real_aws" in item.keywords:
                item.add_marker(skip_real_aws)