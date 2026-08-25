# -*- coding: utf-8 -*-
"""Example test file for demonstrating the automated testing service."""

import pytest


def test_addition():
    """Test basic addition."""
    assert 1 + 1 == 2


def test_subtraction():
    """Test basic subtraction."""
    assert 5 - 3 == 2


def test_multiplication():
    """Test basic multiplication."""
    assert 3 * 4 == 12


def test_division():
    """Test basic division."""
    assert 10 / 2 == 5


@pytest.mark.slow
def test_slow_operation():
    """Test a slow operation."""
    import time
    time.sleep(0.1)
    assert True


@pytest.mark.skip
def test_skipped_example():
    """This test should be skipped."""
    assert False


def test_string_operations():
    """Test string operations."""
    text = "hello"
    assert text.upper() == "HELLO"
    assert text.capitalize() == "Hello"


def test_list_operations():
    """Test list operations."""
    items = [1, 2, 3]
    assert len(items) == 3
    assert 2 in items


def test_dict_operations():
    """Test dictionary operations."""
    data = {"key": "value"}
    assert "key" in data
    assert data["key"] == "value"


class TestMathOperations:
    """Test class for math operations."""

    def test_power(self):
        """Test power operation."""
        assert 2 ** 3 == 8

    def test_modulo(self):
        """Test modulo operation."""
        assert 10 % 3 == 1
