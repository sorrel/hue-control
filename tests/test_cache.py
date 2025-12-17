"""Tests for cache management functions in core/cache.py

NOTE: These are READ-ONLY tests only, following the refactoring testing policy.
No actual cache writes are made during testing - all functions are mocked.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from core.cache import (
    reload_cache,
    is_cache_stale,
    ensure_fresh_cache,
    get_cache_info
)


@pytest.fixture
def mock_controller():
    """Create a mock HueController instance."""
    controller = MagicMock()
    controller.api_token = "test-token-123"
    controller.config = {}
    controller._lights_cache = []
    controller._rooms_cache = []
    controller._scenes_cache = []
    controller._devices_cache = []
    controller._buttons_cache = []
    controller._behaviour_instances_cache = []
    controller._device_power_cache = []
    return controller


class TestReloadCache:
    """Test cache reloading functionality."""

    def test_reload_without_api_token(self, mock_controller):
        """Should fail gracefully when not connected."""
        mock_controller.api_token = None

        result = reload_cache(mock_controller)

        assert result is False

    @patch('core.cache.save_config')
    @patch('core.cache.datetime')
    def test_reload_success(self, mock_datetime, mock_save, mock_controller):
        """Should fetch all resources and save to cache."""
        # Setup mocks
        mock_datetime.now.return_value.isoformat.return_value = "2025-12-11T10:00:00"
        mock_controller.get_lights.return_value = [{'id': 'light1'}]
        mock_controller.get_rooms.return_value = [{'id': 'room1'}]
        mock_controller.get_scenes.return_value = [{'id': 'scene1'}]
        mock_controller.get_devices.return_value = [{'id': 'device1'}]
        mock_controller.get_buttons.return_value = [{'id': 'button1'}]
        mock_controller.get_behaviour_instances.return_value = [{'id': 'behaviour1'}]
        mock_controller.get_device_power.return_value = [{'id': 'power1'}]

        result = reload_cache(mock_controller)

        assert result is True
        assert 'cache' in mock_controller.config
        assert mock_controller.config['cache']['last_updated'] == "2025-12-11T10:00:00"
        assert len(mock_controller.config['cache']['lights']) == 1
        assert len(mock_controller.config['cache']['rooms']) == 1
        assert len(mock_controller.config['cache']['device_power']) == 1
        mock_save.assert_called_once_with(mock_controller.config)

    @patch('core.cache.save_config')
    def test_reload_clears_memory_caches(self, mock_save, mock_controller):
        """Should clear all memory caches before fetching."""
        # Set some initial values
        mock_controller._lights_cache = ['old_data']
        mock_controller._device_power_cache = ['old_battery_data']
        mock_controller.get_lights.return_value = []
        mock_controller.get_rooms.return_value = []
        mock_controller.get_scenes.return_value = []
        mock_controller.get_devices.return_value = []
        mock_controller.get_buttons.return_value = []
        mock_controller.get_behaviour_instances.return_value = []
        mock_controller.get_device_power.return_value = []

        reload_cache(mock_controller)

        # Verify caches were cleared
        assert mock_controller._lights_cache is None
        assert mock_controller._rooms_cache is None
        assert mock_controller._device_power_cache is None

    @patch('core.cache.save_config')
    def test_reload_handles_exception(self, mock_save, mock_controller):
        """Should return False and handle exceptions gracefully."""
        mock_controller.get_lights.side_effect = Exception("API error")

        result = reload_cache(mock_controller)

        assert result is False
        mock_save.assert_not_called()


class TestIsCacheStale:
    """Test cache staleness detection."""

    def test_stale_when_no_cache(self, mock_controller):
        """Should be stale when cache doesn't exist."""
        mock_controller.config = {}

        result = is_cache_stale(mock_controller)

        assert result is True

    def test_stale_when_no_timestamp(self, mock_controller):
        """Should be stale when timestamp is missing."""
        mock_controller.config = {'cache': {}}

        result = is_cache_stale(mock_controller)

        assert result is True

    def test_fresh_when_recently_updated(self, mock_controller):
        """Should be fresh when updated within max_age_hours."""
        now = datetime.now()
        mock_controller.config = {
            'cache': {
                'last_updated': now.isoformat()
            }
        }

        result = is_cache_stale(mock_controller, max_age_hours=24)

        assert result is False

    def test_stale_when_old(self, mock_controller):
        """Should be stale when older than max_age_hours."""
        old_time = datetime.now() - timedelta(hours=25)
        mock_controller.config = {
            'cache': {
                'last_updated': old_time.isoformat()
            }
        }

        result = is_cache_stale(mock_controller, max_age_hours=24)

        assert result is True

    def test_stale_when_invalid_timestamp(self, mock_controller):
        """Should be stale when timestamp is invalid."""
        mock_controller.config = {
            'cache': {
                'last_updated': 'invalid-timestamp'
            }
        }

        result = is_cache_stale(mock_controller)

        assert result is True

    def test_custom_max_age(self, mock_controller):
        """Should respect custom max_age_hours parameter."""
        old_time = datetime.now() - timedelta(hours=2)
        mock_controller.config = {
            'cache': {
                'last_updated': old_time.isoformat()
            }
        }

        # 2 hours old is fresh for 24-hour threshold
        assert is_cache_stale(mock_controller, max_age_hours=24) is False
        # But stale for 1-hour threshold
        assert is_cache_stale(mock_controller, max_age_hours=1) is True


class TestEnsureFreshCache:
    """Test cache freshness enforcement."""

    @patch('core.cache.reload_cache')
    def test_reload_when_no_cache(self, mock_reload, mock_controller):
        """Should reload when cache doesn't exist."""
        mock_controller.config = {}
        mock_reload.return_value = True

        result = ensure_fresh_cache(mock_controller)

        assert result is True
        mock_reload.assert_called_once_with(mock_controller)

    @patch('core.cache.reload_cache')
    @patch('core.cache.is_cache_stale')
    def test_reload_when_stale(self, mock_is_stale, mock_reload, mock_controller):
        """Should reload when cache is stale."""
        mock_controller.config = {'cache': {'last_updated': '2025-01-01T00:00:00'}}
        mock_is_stale.return_value = True
        mock_reload.return_value = True

        result = ensure_fresh_cache(mock_controller)

        assert result is True
        mock_reload.assert_called_once_with(mock_controller)

    @patch('core.cache.is_cache_stale')
    def test_no_reload_when_fresh(self, mock_is_stale, mock_controller):
        """Should not reload when cache is fresh."""
        mock_controller.config = {'cache': {'last_updated': datetime.now().isoformat()}}
        mock_is_stale.return_value = False

        result = ensure_fresh_cache(mock_controller)

        assert result is True

    @patch('core.cache.reload_cache')
    def test_connect_when_no_token(self, mock_reload, mock_controller):
        """Should connect first if no API token."""
        mock_controller.config = {}
        mock_controller.api_token = None
        mock_controller.connect.return_value = True
        mock_reload.return_value = True

        result = ensure_fresh_cache(mock_controller)

        assert result is True
        mock_controller.connect.assert_called_once()

    @patch('core.cache.reload_cache')
    def test_fail_when_cannot_connect(self, mock_reload, mock_controller):
        """Should fail when connection fails."""
        mock_controller.config = {}
        mock_controller.api_token = None
        mock_controller.connect.return_value = False

        result = ensure_fresh_cache(mock_controller)

        assert result is False
        mock_reload.assert_not_called()


class TestGetCacheInfo:
    """Test cache information retrieval."""

    def test_info_when_no_cache(self, mock_controller):
        """Should return exists=False when no cache."""
        mock_controller.config = {}

        info = get_cache_info(mock_controller)

        assert info['exists'] is False
        assert info['last_updated'] is None
        assert info['age_hours'] is None
        assert info['is_stale'] is True
        assert info['counts'] == {}

    def test_info_with_valid_cache(self, mock_controller):
        """Should return full info when cache exists."""
        now = datetime.now()
        mock_controller.config = {
            'cache': {
                'last_updated': now.isoformat(),
                'lights': [{'id': '1'}, {'id': '2'}],
                'rooms': [{'id': 'r1'}],
                'scenes': [{'id': 's1'}, {'id': 's2'}, {'id': 's3'}],
                'devices': [],
                'buttons': [{'id': 'b1'}],
                'behaviours': [{'id': 'bh1'}, {'id': 'bh2'}]
            }
        }

        info = get_cache_info(mock_controller)

        assert info['exists'] is True
        assert info['last_updated'] == now.isoformat()
        assert info['age_hours'] is not None
        assert info['age_hours'] < 0.1  # Very recent
        assert info['is_stale'] is False
        assert info['counts']['lights'] == 2
        assert info['counts']['rooms'] == 1
        assert info['counts']['scenes'] == 3
        assert info['counts']['devices'] == 0
        assert info['counts']['buttons'] == 1
        assert info['counts']['behaviours'] == 2

    def test_info_with_old_cache(self, mock_controller):
        """Should mark as stale when old."""
        old_time = datetime.now() - timedelta(hours=25)
        mock_controller.config = {
            'cache': {
                'last_updated': old_time.isoformat(),
                'lights': []
            }
        }

        info = get_cache_info(mock_controller)

        assert info['exists'] is True
        assert info['is_stale'] is True
        assert info['age_hours'] > 24

    def test_info_with_invalid_timestamp(self, mock_controller):
        """Should handle invalid timestamp gracefully."""
        mock_controller.config = {
            'cache': {
                'last_updated': 'invalid',
                'lights': []
            }
        }

        info = get_cache_info(mock_controller)

        assert info['exists'] is True
        assert info['age_hours'] is None
        assert info['is_stale'] is True

    def test_info_includes_device_power_count(self, mock_controller):
        """Should include device_power resource count in cache info."""
        now = datetime.now()
        mock_controller.config = {
            'cache': {
                'last_updated': now.isoformat(),
                'lights': [],
                'rooms': [],
                'scenes': [],
                'devices': [],
                'buttons': [],
                'behaviours': [],
                'device_power': [
                    {'id': 'power1', 'power_state': {'battery_level': 85, 'battery_state': 'normal'}},
                    {'id': 'power2', 'power_state': {'battery_level': 25, 'battery_state': 'low'}},
                    {'id': 'power3', 'power_state': {'battery_level': 5, 'battery_state': 'critical'}}
                ]
            }
        }

        info = get_cache_info(mock_controller)

        assert info['exists'] is True
        assert info['counts']['device_power'] == 3


class TestDevicePowerCaching:
    """Test device_power battery data caching functionality."""

    @patch('core.cache.save_config')
    @patch('core.cache.datetime')
    def test_reload_fetches_device_power(self, mock_datetime, mock_save, mock_controller):
        """Should fetch device_power resources during reload."""
        mock_datetime.now.return_value.isoformat.return_value = "2025-12-17T10:00:00"
        mock_controller.get_lights.return_value = []
        mock_controller.get_rooms.return_value = []
        mock_controller.get_scenes.return_value = []
        mock_controller.get_devices.return_value = []
        mock_controller.get_buttons.return_value = []
        mock_controller.get_behaviour_instances.return_value = []
        mock_controller.get_device_power.return_value = [
            {
                'id': 'power1',
                'power_state': {
                    'battery_level': 85,
                    'battery_state': 'normal'
                }
            },
            {
                'id': 'power2',
                'power_state': {
                    'battery_level': 15,
                    'battery_state': 'low'
                }
            }
        ]

        result = reload_cache(mock_controller)

        assert result is True
        assert 'device_power' in mock_controller.config['cache']
        assert len(mock_controller.config['cache']['device_power']) == 2
        assert mock_controller.config['cache']['device_power'][0]['id'] == 'power1'
        assert mock_controller.config['cache']['device_power'][0]['power_state']['battery_level'] == 85
        assert mock_controller.config['cache']['device_power'][1]['power_state']['battery_state'] == 'low'
        mock_controller.get_device_power.assert_called_once()

    @patch('core.cache.save_config')
    def test_reload_battery_states(self, mock_save, mock_controller):
        """Should cache all three battery states: normal, low, critical."""
        mock_controller.get_lights.return_value = []
        mock_controller.get_rooms.return_value = []
        mock_controller.get_scenes.return_value = []
        mock_controller.get_devices.return_value = []
        mock_controller.get_buttons.return_value = []
        mock_controller.get_behaviour_instances.return_value = []
        mock_controller.get_device_power.return_value = [
            {'id': 'p1', 'power_state': {'battery_level': 90, 'battery_state': 'normal'}},
            {'id': 'p2', 'power_state': {'battery_level': 25, 'battery_state': 'low'}},
            {'id': 'p3', 'power_state': {'battery_level': 5, 'battery_state': 'critical'}}
        ]

        reload_cache(mock_controller)

        device_power = mock_controller.config['cache']['device_power']
        assert len(device_power) == 3

        # Verify normal state
        normal = [p for p in device_power if p['power_state']['battery_state'] == 'normal']
        assert len(normal) == 1
        assert normal[0]['power_state']['battery_level'] == 90

        # Verify low state
        low = [p for p in device_power if p['power_state']['battery_state'] == 'low']
        assert len(low) == 1
        assert low[0]['power_state']['battery_level'] == 25

        # Verify critical state
        critical = [p for p in device_power if p['power_state']['battery_state'] == 'critical']
        assert len(critical) == 1
        assert critical[0]['power_state']['battery_level'] == 5
