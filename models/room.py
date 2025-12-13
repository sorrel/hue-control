"""Room configuration operations.

This module handles saving, comparing, and (future) restoring room configurations.
Room configurations include metadata, lights, scenes, and behaviour instances.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, TYPE_CHECKING
import click

if TYPE_CHECKING:
    from hue_control import HueController

# Constants
SAVED_ROOMS_DIR = Path(__file__).parent.parent / 'cache' / 'saved-rooms'


def save_room_configuration(controller: 'HueController', room_name: str) -> Optional[str]:
    """Save complete configuration for a room to a timestamped file.

    Extracts from cache:
    - Room metadata
    - All lights in the room with their current states
    - All scenes for the room
    - All behaviour instances (switch configurations) targeting the room

    Args:
        controller: HueController instance
        room_name: Name of the room to save (case-insensitive substring match)

    Returns:
        Path to saved file if successful, None otherwise
    """
    if not controller.use_cache:
        click.echo("Error: save_room_configuration requires cache to be loaded.")
        return None

    cache = controller.config.get('cache', {})
    if not cache:
        click.echo("Error: No cache data available.")
        return None

    # Find the room
    rooms = cache.get('rooms', [])
    matching_rooms = [r for r in rooms if room_name.lower() in r.get('metadata', {}).get('name', '').lower()]

    if not matching_rooms:
        click.echo(f"Error: No room found matching '{room_name}'.")
        return None

    if len(matching_rooms) > 1:
        click.echo(f"Error: Multiple rooms match '{room_name}':")
        for r in matching_rooms:
            click.echo(f"  - {r.get('metadata', {}).get('name', 'Unknown')}")
        return None

    room = matching_rooms[0]
    room_id = room['id']
    room_full_name = room.get('metadata', {}).get('name', 'Unknown')

    # Get device RIDs in this room
    device_rids = [c['rid'] for c in room.get('children', []) if c['rtype'] == 'device']

    # Extract lights for this room
    lights = cache.get('lights', [])
    room_lights = [l for l in lights if l.get('owner', {}).get('rid') in device_rids]

    # Extract scenes for this room
    scenes = cache.get('scenes', [])
    room_scenes = [s for s in scenes if s.get('group', {}).get('rid') == room_id]

    # Extract behaviours targeting this room
    behaviours = cache.get('behaviours', [])
    room_behaviours = []

    for b in behaviours:
        config = b.get('configuration', {})
        where_rids = []

        # Extract all 'where' references
        if 'where' in config:
            for w in config['where']:
                if w.get('group', {}).get('rtype') == 'room':
                    where_rids.append(w.get('group', {}).get('rid'))

        # Check button-specific where (old format)
        for key in ['button1', 'button2', 'button3', 'button4', 'rotary']:
            if key in config and 'where' in config[key]:
                for w in config[key]['where']:
                    if w.get('group', {}).get('rtype') == 'room':
                        where_rids.append(w.get('group', {}).get('rid'))

        # Check new format
        if 'buttons' in config:
            for button_rid, button_config in config['buttons'].items():
                if 'where' in button_config:
                    for w in button_config['where']:
                        if w.get('group', {}).get('rtype') == 'room':
                            where_rids.append(w.get('group', {}).get('rid'))

        # If this behaviour targets our room, include it
        if room_id in where_rids:
            room_behaviours.append(b)

    # Create saved configuration
    saved_config = {
        'saved_at': datetime.now().isoformat(),
        'room': room,
        'lights': room_lights,
        'scenes': room_scenes,
        'behaviours': room_behaviours,
        'summary': {
            'room_name': room_full_name,
            'light_count': len(room_lights),
            'scene_count': len(room_scenes),
            'behaviour_count': len(room_behaviours),
            'device_count': len(device_rids),
        }
    }

    # Create filename: YYYY-MM-DD_HH-MM_RoomName.json
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    # Sanitise room name for filename
    safe_room_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in room_full_name)
    safe_room_name = safe_room_name.replace(' ', '_')
    filename = f"{timestamp}_{safe_room_name}.json"

    # Ensure directory exists
    SAVED_ROOMS_DIR.mkdir(parents=True, exist_ok=True)

    # Save to file
    filepath = SAVED_ROOMS_DIR / filename

    with open(filepath, 'w') as f:
        json.dump(saved_config, f, indent=2)

    return str(filepath)


def diff_room_configuration(controller: 'HueController', saved_file_path: str, verbose: bool = False) -> Optional[Dict]:
    """Compare saved room configuration with current cache.

    Performs section-by-section comparison:
    - Room metadata changes
    - Lights: added/removed (verbose: + state changes like on/off, brightness, colour temp)
    - Scenes: added/removed/changed (auto_dynamic, action count)
    - Behaviours: added/removed/changed (enabled state)

    Args:
        controller: HueController instance
        saved_file_path: Path to saved room JSON file
        verbose: If True, include ephemeral state changes (light levels, on/off)

    Returns:
        Dict with diff results, or None if error
    """
    if not controller.use_cache:
        click.echo("Error: diff_room_configuration requires cache to be loaded.")
        return None

    try:
        # Load saved configuration
        with open(saved_file_path, 'r') as f:
            saved = json.load(f)

        # Get current configuration for the same room
        room_name = saved['summary']['room_name']
        cache = controller.config.get('cache', {})

        # Find the room in current cache
        rooms = cache.get('rooms', [])
        current_room = None
        for r in rooms:
            if r.get('metadata', {}).get('name', '') == room_name:
                current_room = r
                break

        if not current_room:
            return {
                'error': f"Room '{room_name}' not found in current cache",
                'room_deleted': True
            }

        room_id = current_room['id']
        device_rids = [c['rid'] for c in current_room.get('children', []) if c['rtype'] == 'device']

        # Get current data for comparison
        current_lights = [l for l in cache.get('lights', []) if l.get('owner', {}).get('rid') in device_rids]
        current_scenes = [s for s in cache.get('scenes', []) if s.get('group', {}).get('rid') == room_id]
        current_behaviours = []

        # Extract current behaviours for this room (same logic as save)
        for b in cache.get('behaviours', []):
            config = b.get('configuration', {})
            where_rids = []

            if 'where' in config:
                for w in config['where']:
                    if w.get('group', {}).get('rtype') == 'room':
                        where_rids.append(w.get('group', {}).get('rid'))

            for key in ['button1', 'button2', 'button3', 'button4', 'rotary']:
                if key in config and 'where' in config[key]:
                    for w in config[key]['where']:
                        if w.get('group', {}).get('rtype') == 'room':
                            where_rids.append(w.get('group', {}).get('rid'))

            if 'buttons' in config:
                for button_rid, button_config in config['buttons'].items():
                    if 'where' in button_config:
                        for w in button_config['where']:
                            if w.get('group', {}).get('rtype') == 'room':
                                where_rids.append(w.get('group', {}).get('rid'))

            if room_id in where_rids:
                current_behaviours.append(b)

        # Compare sections
        diff = {
            'room_name': room_name,
            'saved_at': saved['saved_at'],
            'compared_at': datetime.now().isoformat(),
            'verbose': verbose,
            'room': _diff_room_metadata(saved['room'], current_room),
            'lights': _diff_lights(saved['lights'], current_lights, verbose),
            'scenes': _diff_scenes(saved['scenes'], current_scenes),
            'behaviours': _diff_behaviours(saved['behaviours'], current_behaviours),
        }

        return diff

    except Exception as e:
        return {'error': str(e)}


def _diff_room_metadata(saved_room: dict, current_room: dict) -> Dict:
    """Compare room metadata."""
    changes = []

    # Check basic metadata
    saved_meta = saved_room.get('metadata', {})
    current_meta = current_room.get('metadata', {})

    if saved_meta.get('name') != current_meta.get('name'):
        changes.append(f"Name: '{saved_meta.get('name')}' → '{current_meta.get('name')}'")

    if saved_meta.get('archetype') != current_meta.get('archetype'):
        changes.append(f"Archetype: '{saved_meta.get('archetype')}' → '{current_meta.get('archetype')}'")

    # Check device count
    saved_devices = len([c for c in saved_room.get('children', []) if c['rtype'] == 'device'])
    current_devices = len([c for c in current_room.get('children', []) if c['rtype'] == 'device'])

    if saved_devices != current_devices:
        changes.append(f"Device count: {saved_devices} → {current_devices}")

    return {
        'changed': len(changes) > 0,
        'changes': changes
    }


def _diff_lights(saved_lights: List[dict], current_lights: List[dict], verbose: bool = False) -> Dict:
    """Compare lights - added, removed, and optionally state changes.

    Args:
        saved_lights: Saved light configurations
        current_lights: Current light configurations
        verbose: If True, include ephemeral state changes (on/off, brightness, colour temp)

    Returns:
        Dict with added, removed, changed lists and summary
    """
    # Create lookup by ID
    saved_by_id = {l['id']: l for l in saved_lights}
    current_by_id = {l['id']: l for l in current_lights}

    added = []
    removed = []
    changed = []

    # Find added lights
    for light_id, light in current_by_id.items():
        if light_id not in saved_by_id:
            added.append(light.get('metadata', {}).get('name', 'Unknown'))

    # Find removed and changed lights
    for light_id, saved_light in saved_by_id.items():
        if light_id not in current_by_id:
            removed.append(saved_light.get('metadata', {}).get('name', 'Unknown'))
        elif verbose:
            # Only compare state changes in verbose mode
            current_light = current_by_id[light_id]
            light_changes = []

            # Compare on/off
            saved_on = saved_light.get('on', {}).get('on')
            current_on = current_light.get('on', {}).get('on')
            if saved_on != current_on:
                light_changes.append(f"on: {saved_on} → {current_on}")

            # Compare brightness
            saved_bri = saved_light.get('dimming', {}).get('brightness')
            current_bri = current_light.get('dimming', {}).get('brightness')
            if saved_bri is not None and current_bri is not None:
                if abs(saved_bri - current_bri) > 0.5:  # Ignore tiny differences
                    light_changes.append(f"brightness: {saved_bri:.1f}% → {current_bri:.1f}%")

            # Compare colour temperature
            saved_ct = saved_light.get('color_temperature', {}).get('mirek')
            current_ct = current_light.get('color_temperature', {}).get('mirek')
            if saved_ct is not None and current_ct is not None:
                if saved_ct != current_ct:
                    light_changes.append(f"colour temp: {saved_ct} → {current_ct}")

            if light_changes:
                name = saved_light.get('metadata', {}).get('name', 'Unknown')
                changed.append({'name': name, 'changes': light_changes})

    return {
        'added': added,
        'removed': removed,
        'changed': changed,
        'summary': f"{len(added)} added, {len(removed)} removed" + (f", {len(changed)} changed" if verbose and changed else "")
    }


def _diff_scenes(saved_scenes: List[dict], current_scenes: List[dict]) -> Dict:
    """Compare scenes - added, removed, and setting changes."""
    saved_by_id = {s['id']: s for s in saved_scenes}
    current_by_id = {s['id']: s for s in current_scenes}

    added = []
    removed = []
    changed = []

    # Find added scenes
    for scene_id, scene in current_by_id.items():
        if scene_id not in saved_by_id:
            added.append(scene.get('metadata', {}).get('name', 'Unknown'))

    # Find removed and changed scenes
    for scene_id, saved_scene in saved_by_id.items():
        if scene_id not in current_by_id:
            removed.append(saved_scene.get('metadata', {}).get('name', 'Unknown'))
        else:
            current_scene = current_by_id[scene_id]
            scene_changes = []

            # Compare auto_dynamic
            saved_auto = saved_scene.get('auto_dynamic', False)
            current_auto = current_scene.get('auto_dynamic', False)
            if saved_auto != current_auto:
                scene_changes.append(f"auto_dynamic: {saved_auto} → {current_auto}")

            # Compare action count
            saved_actions = len(saved_scene.get('actions', []))
            current_actions = len(current_scene.get('actions', []))
            if saved_actions != current_actions:
                scene_changes.append(f"light count: {saved_actions} → {current_actions}")

            # Compare speed
            saved_speed = saved_scene.get('speed')
            current_speed = current_scene.get('speed')
            if saved_speed is not None and current_speed is not None:
                if abs(saved_speed - current_speed) > 0.01:
                    scene_changes.append(f"speed: {saved_speed:.2f} → {current_speed:.2f}")

            if scene_changes:
                name = saved_scene.get('metadata', {}).get('name', 'Unknown')
                changed.append({'name': name, 'changes': scene_changes})

    return {
        'added': added,
        'removed': removed,
        'changed': changed,
        'summary': f"{len(added)} added, {len(removed)} removed, {len(changed)} changed"
    }


def _diff_behaviours(saved_behaviours: List[dict], current_behaviours: List[dict]) -> Dict:
    """Compare behaviour instances - added, removed, and state changes."""
    saved_by_id = {b['id']: b for b in saved_behaviours}
    current_by_id = {b['id']: b for b in current_behaviours}

    added = []
    removed = []
    changed = []

    # Find added behaviours
    for behav_id, behav in current_by_id.items():
        if behav_id not in saved_by_id:
            added.append(behav.get('metadata', {}).get('name', 'Unknown'))

    # Find removed and changed behaviours
    for behav_id, saved_behav in saved_by_id.items():
        if behav_id not in current_by_id:
            removed.append(saved_behav.get('metadata', {}).get('name', 'Unknown'))
        else:
            current_behav = current_by_id[behav_id]
            behav_changes = []

            # Compare enabled state
            saved_enabled = saved_behav.get('enabled', False)
            current_enabled = current_behav.get('enabled', False)
            if saved_enabled != current_enabled:
                behav_changes.append(f"enabled: {saved_enabled} → {current_enabled}")

            # Compare status
            saved_status = saved_behav.get('status', '')
            current_status = current_behav.get('status', '')
            if saved_status != current_status:
                behav_changes.append(f"status: {saved_status} → {current_status}")

            if behav_changes:
                name = saved_behav.get('metadata', {}).get('name', 'Unknown')
                changed.append({'name': name, 'changes': behav_changes})

    return {
        'added': added,
        'removed': removed,
        'changed': changed,
        'summary': f"{len(added)} added, {len(removed)} removed, {len(changed)} changed"
    }
