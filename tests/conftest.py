"""Pytest configuration and fixtures for Hue backup tests."""

import pytest
from pathlib import Path

@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent

@pytest.fixture
def cache_dir(project_root):
    """Return the cache directory path."""
    return project_root / "cache.nosync"

@pytest.fixture
def saved_rooms_dir(project_root):
    """Return the saved-rooms directory path."""
    return project_root / "saved-rooms"
