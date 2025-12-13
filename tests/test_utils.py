"""Tests for utility functions in models/utils.py"""

import pytest
from models.utils import display_width, decode_button_event, create_name_lookup


class TestDisplayWidth:
    """Tests for display_width function."""

    def test_ascii_text(self):
        """ASCII text should have width equal to length."""
        assert display_width("hello") == 5
        assert display_width("test") == 4
        assert display_width("") == 0

    def test_battery_emoji(self):
        """Battery emoji should count as 2 columns."""
        assert display_width("🔋") == 2
        assert display_width("🪫") == 2

    def test_arrow_symbol(self):
        """Arrow symbol should count as 2 columns."""
        assert display_width("→") == 2

    def test_mixed_content(self):
        """Mixed ASCII and emojis should sum correctly."""
        assert display_width("Battery: 🔋") == 11  # 9 ASCII + 2 emoji
        assert display_width("A → B") == 6  # 4 ASCII + 2 arrow

    def test_high_unicode(self):
        """High Unicode characters (>0x1F300) should count as 2."""
        # Most emojis are above 0x1F300
        assert display_width("😀") == 2
        assert display_width("🎉") == 2


class TestDecodeButtonEvent:
    """Tests for decode_button_event function."""

    def test_on_button_short_release(self):
        """On button (1) short release (002)."""
        assert decode_button_event(1002) == "On (Short Release)"

    def test_dim_up_hold(self):
        """Dim Up button (2) hold (001)."""
        assert decode_button_event(2001) == "Dim Up (Hold)"

    def test_dim_down_initial_press(self):
        """Dim Down button (3) initial press (000)."""
        assert decode_button_event(3000) == "Dim Down (Initial Press)"

    def test_off_button_long_release(self):
        """Off button (4) long release (003)."""
        assert decode_button_event(4003) == "Off (Long Release)"

    def test_dial_rotate(self):
        """Dial rotate (34) short release (002)."""
        assert decode_button_event(34002) == "Dial Rotate (Short Release)"

    def test_dial_press(self):
        """Dial press (35) initial press (000)."""
        assert decode_button_event(35000) == "Dial Press (Initial Press)"

    def test_unknown_event_code(self):
        """Unknown or invalid event codes."""
        assert decode_button_event(0) == "Unknown"
        assert decode_button_event(None) == "Unknown"
        assert "Unknown" in decode_button_event(99)


class TestCreateNameLookup:
    """Tests for create_name_lookup function."""

    def test_empty_list(self):
        """Empty resource list should return empty dict."""
        assert create_name_lookup([]) == {}

    def test_single_resource(self):
        """Single resource should map ID to name."""
        resources = [
            {'id': 'light-1', 'metadata': {'name': 'Living Room Lamp'}}
        ]
        result = create_name_lookup(resources)
        assert result == {'light-1': 'Living Room Lamp'}

    def test_multiple_resources(self):
        """Multiple resources should all be mapped."""
        resources = [
            {'id': 'light-1', 'metadata': {'name': 'Lamp 1'}},
            {'id': 'light-2', 'metadata': {'name': 'Lamp 2'}},
            {'id': 'light-3', 'metadata': {'name': 'Lamp 3'}},
        ]
        result = create_name_lookup(resources)
        assert len(result) == 3
        assert result['light-1'] == 'Lamp 1'
        assert result['light-2'] == 'Lamp 2'
        assert result['light-3'] == 'Lamp 3'

    def test_missing_metadata(self):
        """Resources without metadata should map to 'Unknown'."""
        resources = [
            {'id': 'light-1'},
            {'id': 'light-2', 'metadata': {}},
        ]
        result = create_name_lookup(resources)
        assert result['light-1'] == 'Unknown'
        assert result['light-2'] == 'Unknown'

    def test_missing_name(self):
        """Resources with metadata but no name should map to 'Unknown'."""
        resources = [
            {'id': 'light-1', 'metadata': {'archetype': 'lamp'}}
        ]
        result = create_name_lookup(resources)
        assert result['light-1'] == 'Unknown'
