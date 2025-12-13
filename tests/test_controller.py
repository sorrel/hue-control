"""
Tests for HueController delegation methods and utility imports.

These tests verify that HueController methods properly delegate to
the corresponding functions in core modules, and that required
utilities are properly imported.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.controller import HueController, BUTTON_LABELS_EXTENDED


class TestImports:
    """Test that required utilities are properly imported."""

    def test_create_name_lookup_imported(self):
        """Test that create_name_lookup is imported from models.utils.

        This test was added after fixing a bug where scene-details failed
        because create_name_lookup was used but not imported.
        """
        from core.controller import create_name_lookup
        assert callable(create_name_lookup)

    def test_button_labels_defined(self):
        """Test that BUTTON_LABELS_EXTENDED is defined.

        This test was added after fixing a bug where get_scene_to_switch_mapping
        referenced BUTTON_LABELS_EXTENDED which was not defined.
        """
        assert isinstance(BUTTON_LABELS_EXTENDED, dict)
        assert 1 in BUTTON_LABELS_EXTENDED
        assert BUTTON_LABELS_EXTENDED[1] == 'ON'
        assert 34 in BUTTON_LABELS_EXTENDED  # Dial rotate
        assert 35 in BUTTON_LABELS_EXTENDED  # Dial press


class TestCacheDelegation:
    """Test that HueController cache methods delegate correctly."""

    @patch('core.controller.reload_cache')
    def test_reload_cache_delegates(self, mock_reload):
        """Test reload_cache() delegates to core.cache.reload_cache()."""
        mock_reload.return_value = True
        controller = HueController()

        result = controller.reload_cache()

        assert result is True
        mock_reload.assert_called_once_with(controller)

    @patch('core.controller.is_cache_stale')
    def test_is_cache_stale_delegates(self, mock_stale):
        """Test is_cache_stale() delegates to core.cache.is_cache_stale()."""
        mock_stale.return_value = True
        controller = HueController()

        result = controller.is_cache_stale(max_age_hours=12)

        assert result is True
        mock_stale.assert_called_once_with(controller, 12)

    @patch('core.controller.ensure_fresh_cache')
    def test_ensure_fresh_cache_delegates(self, mock_ensure):
        """Test ensure_fresh_cache() delegates to core.cache.ensure_fresh_cache().

        This test was added after fixing a bug where ensure_fresh_cache()
        had incorrect code that tried to reference undefined variables.
        """
        mock_ensure.return_value = True
        controller = HueController()

        result = controller.ensure_fresh_cache(max_age_hours=24)

        assert result is True
        mock_ensure.assert_called_once_with(controller, 24)
