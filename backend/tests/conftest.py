"""
backend/tests/conftest.py
-------------------------
Shared test fixtures and setup for backend test suite.
"""

import pytest

from app.core.ratelimit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state before each test to guarantee test isolation."""
    try:
        limiter.reset()
    except Exception:
        pass
    yield
    try:
        limiter.reset()
    except Exception:
        pass
