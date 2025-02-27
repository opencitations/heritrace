"""
Basic tests to verify that the testing infrastructure is working correctly.
"""

import pytest


def test_basic_assertion():
    """A simple test that should always pass."""
    assert True


def test_basic_math():
    """Test basic math operations."""
    assert 1 + 1 == 2
    assert 2 * 3 == 6
    assert 10 / 2 == 5
    assert 10 - 5 == 5
