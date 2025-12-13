"""Utility functions for Hue control.

This module contains helper functions used across the application:
- display_width: Calculate terminal display width for Unicode/emojis
- decode_button_event: Convert button event codes to human-readable format
- create_name_lookup: Build ID-to-name mappings for resources
- get_cache_controller: Helper to create cache-enabled controllers
"""

import click
from typing import Optional, List, Dict


def display_width(text: str) -> int:
    """Calculate the display width of text accounting for wide characters.

    Emojis and certain Unicode characters take up 2 columns in the terminal.
    """
    width = 0
    for char in text:
        # Common emojis and symbols that take 2 columns
        if char in '🔋🪫→':
            width += 2
        # Most emoji characters are in these ranges
        elif ord(char) > 0x1F300:
            width += 2
        else:
            width += 1
    return width


def decode_button_event(event_code: int) -> str:
    """Decode a Hue button event code into human-readable format.

    Format: XYYY where X is button number, YYY is event type
    Button: 1=On, 2=Dim Up, 3=Dim Down, 4=Off, 5=Special
    Event: 000=Initial Press, 001=Hold, 002=Short Release, 003=Long Release
    """
    if not event_code:
        return "Unknown"

    event_str = str(event_code)
    if len(event_str) < 4:
        return f"Unknown ({event_code})"

    button_map = {
        '1': 'On',
        '2': 'Dim Up',
        '3': 'Dim Down',
        '4': 'Off',
        '5': 'Special',
        '34': 'Dial Rotate',
        '35': 'Dial Press',
    }

    event_map = {
        '000': 'Initial Press',
        '001': 'Hold',
        '002': 'Short Release',
        '003': 'Long Release',
    }

    # Handle tap dial special cases
    if event_str.startswith('34') or event_str.startswith('35'):
        button = event_str[:2]
        event = event_str[2:]
        button_name = button_map.get(button, button)
        event_type = event_map.get(event, event)
        return f"{button_name} ({event_type})"

    button = event_str[0]
    event = event_str[1:]

    button_name = button_map.get(button, f"Button {button}")
    event_type = event_map.get(event, event)

    return f"{button_name} ({event_type})"


def create_name_lookup(resources: List[dict]) -> Dict[str, str]:
    """Create a lookup dict mapping resource IDs to names.

    Args:
        resources: List of v2 API resource dicts with 'id' and 'metadata.name' fields

    Returns:
        Dict mapping resource ID to name
    """
    return {r['id']: r.get('metadata', {}).get('name', 'Unknown') for r in resources}


def get_cache_controller(auto_reload: bool = True):
    """Get a cache-enabled controller with optional auto-reload.

    This helper reduces boilerplate in cache-based commands.

    Args:
        auto_reload: Whether to auto-reload stale cache

    Returns:
        A cache-enabled HueController, or None if cache couldn't be prepared
    """
    # Import here to avoid circular dependency
    # HueController will be in core.controller after Phase 6
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from hue_control import HueController

    cache_ctrl = HueController(use_cache=True)
    if auto_reload:
        if not cache_ctrl.ensure_fresh_cache():
            click.echo("Failed to ensure fresh cache.")
            return None
    return cache_ctrl
