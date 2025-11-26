"""Configuration for picker flow tests - no infrastructure required."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def test_infrastructure():
    """Override to skip infrastructure for picker API tests."""
    yield  # These tests use HTTP mocking, not real infrastructure
