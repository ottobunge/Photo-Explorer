"""Unit test configuration - disables test infrastructure.

Unit tests use mocks instead of real infrastructure.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def test_infrastructure():
    """Override test_infrastructure fixture for unit tests.

    Unit tests don't need Docker infrastructure - they use mocks.
    This fixture overrides the session-scoped fixture from tests/conftest.py
    to prevent starting Docker containers for unit tests.
    """
    # No-op for unit tests
    yield
