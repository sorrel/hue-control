"""
Button mapping commands for switch-to-scene mappings and monitoring.

These commands manage local button-to-scene mappings configured in this CLI tool.
"""

import click
import time
from core.controller import HueController


@click.command()
@click.argument('sensor_id')
@click.argument('button_event', type=int)
@click.argument('scene_id')
def map_command(sensor_id: str, button_event: int, scene_id: str):
    """Map a button event to a scene.

    \b
    Examples:
      uv run python hue_control.py map 2 1002 abc123
      This maps button event 1002 on sensor 2 to scene abc123.

    \b
    To find values:
      - Use 'switches' to see sensor IDs
      - Use 'discover' to find button event codes
      - Use 'scenes' to see scene IDs
    """
    controller = HueController()
    if not controller.connect():
        return

    # Verify sensor exists
    sensors = controller.get_sensors()
    if sensor_id not in sensors:
        click.echo(f"Error: Sensor ID '{sensor_id}' not found.")
        click.echo("Use 'switches' command to see available sensors.")
        click.echo()
        return

    # Verify scene exists
    scenes = controller.get_scenes()
    if scene_id not in scenes:
        click.echo(f"Error: Scene ID '{scene_id}' not found.")
        click.echo("Use 'scenes' command to see available scenes.")
        click.echo()
        return

    # Create mapping
    controller.map_button_to_scene(sensor_id, button_event, scene_id)

    sensor_name = sensors[sensor_id].get('name', 'Unknown')
    scene_name = scenes[scene_id].get('name', 'Unknown')

    click.echo(f"\n✓ Mapping created:")
    click.echo(f"  Switch: {sensor_name} (ID: {sensor_id})")
    click.echo(f"  Button event: {button_event}")
    click.echo(f"  Scene: {scene_name} (ID: {scene_id})")
    click.echo(f"\nRun 'monitor' to activate this mapping.")


@click.command()
def mappings_command():
    """List all current button-to-scene mappings."""
    controller = HueController()
    if not controller.connect():
        return

    if not controller.button_mappings:
        click.echo("No button mappings configured yet.")
        click.echo("\nUse 'map' command to create mappings.")
        click.echo()
        return

    sensors = controller.get_sensors()
    scenes = controller.get_scenes()

    click.echo("\nConfigured button mappings:\n")
    for mapping_key, scene_id in controller.button_mappings.items():
        sensor_id, button_event = mapping_key.split(':')

        sensor_name = sensors.get(sensor_id, {}).get('name', 'Unknown')
        scene_name = scenes.get(scene_id, {}).get('name', 'Unknown')

        click.echo(f"  • {sensor_name} (ID: {sensor_id})")
        click.echo(f"    Button event: {button_event}")
        click.echo(f"    → Scene: {scene_name} (ID: {scene_id})")
        click.echo()


@click.command()
def discover_command():
    """Discover button events by pressing buttons on your switches.

    This helps you find out which button event codes are generated
    when you press different buttons on your switches.
    """
    controller = HueController()
    if not controller.connect():
        return

    click.echo("Press buttons on your switches to see their event codes...\n")

    def on_button_event(sensor_id, event_data):
        click.echo(f"Button pressed!")
        click.echo(f"  Switch: {event_data['name']} (ID: {sensor_id})")
        click.echo(f"  Event code: {event_data['buttonevent']}")
        click.echo()

    controller.monitor_buttons(on_button_event)


@click.command()
def monitor_command():
    """Monitor switches and activate mapped scenes when buttons are pressed.

    This is the main runtime command that watches for button presses
    and triggers the scenes you've configured with the 'map' command.
    """
    controller = HueController()
    if not controller.connect():
        return

    if not controller.button_mappings:
        click.echo("No button mappings configured.")
        click.echo("Use 'map' command to set up mappings first.")
        click.echo()
        return

    click.echo("Active mappings:")
    sensors = controller.get_sensors()
    scenes = controller.get_scenes()

    for mapping_key, scene_id in controller.button_mappings.items():
        sensor_id, button_event = mapping_key.split(':')
        sensor_name = sensors.get(sensor_id, {}).get('name', 'Unknown')
        scene_name = scenes.get(scene_id, {}).get('name', 'Unknown')
        click.echo(f"  • {sensor_name} button {button_event} → {scene_name}")

    click.echo()

    def on_button_event(sensor_id, event_data):
        button_event = event_data['buttonevent']
        mapping_key = f"{sensor_id}:{button_event}"

        if mapping_key in controller.button_mappings:
            scene_id = controller.button_mappings[mapping_key]
            scene_name = scenes.get(scene_id, {}).get('name', 'Unknown')

            click.echo(f"[{time.strftime('%H:%M:%S')}] {event_data['name']} → Activating '{scene_name}'")

            if not controller.activate_scene(scene_id):
                click.echo(f"  Error: Failed to activate scene")

    controller.monitor_buttons(on_button_event)
