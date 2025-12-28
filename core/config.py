"""Configuration management and 1Password integration.

This module handles:
- Loading/saving configuration files
- 1Password CLI integration for API token retrieval
- Button mapping persistence
"""

import json
import subprocess
from pathlib import Path

# Configuration file paths
CONFIG_FILE = Path(__file__).parent.parent / 'cache.nosync' / 'hue_data.json'
USER_CONFIG_FILE = Path.home() / '.hue_backup' / 'config.json'


def is_op_available() -> bool:
    """Check if 1Password CLI is available."""
    try:
        result = subprocess.run(['op', '--version'],
                              capture_output=True,
                              timeout=2)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def load_config() -> dict:
    """Load configuration from local file (button mappings and cache).

    Returns:
        Dict with 'button_mappings' and optionally 'cache' keys
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'button_mappings': {}}


def save_config(config: dict):
    """Save configuration to file.

    Args:
        config: Configuration dict to save
    """
    # Create cache directory if it doesn't exist
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Save to local file
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
