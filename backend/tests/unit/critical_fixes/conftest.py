"""Configuration for critical fixes unit tests.

These are pure unit tests that don't require infrastructure.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def test_infrastructure():
    """Override the global fixture to skip infrastructure for unit tests."""
    yield  # No infrastructure needed for unit tests
