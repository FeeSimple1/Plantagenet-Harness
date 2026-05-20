"""Shared pytest fixtures for the Plantagenet harness test suite."""

from __future__ import annotations

import pytest

from plantagenet import static_data


@pytest.fixture(scope="session")
def forces():
    return static_data.load_forces()


@pytest.fixture(scope="session")
def locales():
    return static_data.load_locales()


@pytest.fixture(scope="session")
def ways():
    return static_data.load_ways()


@pytest.fixture(scope="session")
def lords():
    return static_data.load_lords()


@pytest.fixture(scope="session")
def vassals():
    return static_data.load_vassals()
