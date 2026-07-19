import click

from olh.commands._resolve import (
    fetch_channels,
    resolve_rgb_profile,
    resolve_targets,
    rgb_profiles_by_device,
)
from olh.context import CliContext
from olh.output import print_ack


@click.group("light")
def light() -> None:
    """Set RGB lighting and brightness by channel label, or everywhere at once."""


@light.command("list")
@click.pass_obj
def list_lights(obj: CliContext) -> None:
    """Every channel with its current RGB profile."""
    rows = [
        {
            "label": c.label,
            "channel": c.channel_id,
            "type": c.description,
            "rgb": c.rgb,
            "device": c.device_id,
        }
        for c in fetch_channels(obj.client)
    ]
    obj.render(rows)


@light.command("profiles")
@click.pass_obj
def list_profiles(obj: CliContext) -> None:
    """Available RGB effect names, per device."""
    rows = [
        {"device": device_id, "profiles": profiles}
        for device_id, profiles in rgb_profiles_by_device(obj.client).items()
    ]
    obj.render(rows)


@light.command("set")
@click.argument("name_or_profile")
@click.argument("profile", required=False)
@click.pass_obj
def set_light(obj: CliContext, name_or_profile: str, profile: str | None) -> None:
    """Apply an RGB profile: `light set rainbow` for every channel, or
    `light set pump rainbow` for one (label, "pump", channel id, or "all")."""
    if profile is None:
        name, wanted = "all", name_or_profile
    else:
        name, wanted = name_or_profile, profile
    channels = fetch_channels(obj.client)
    if not channels:
        raise click.UsageError("No channels found on any device.")
    targets = resolve_targets(channels, name)
    by_device = rgb_profiles_by_device(obj.client)
    # Resolve every target's profile name before posting anything, so a typo
    # doesn't apply to one device and then error on the next.
    resolved = [
        (device_id, channel_id, resolve_rgb_profile(by_device, device_id, wanted))
        for device_id, channel_id in targets
    ]
    for device_id, channel_id, canonical in resolved:
        payload = {"deviceId": device_id, "channelId": channel_id, "profile": canonical}
        print_ack(obj.client.post("/api/color", json=payload))


@light.command("brightness")
@click.argument("value", type=click.IntRange(0, 100))
@click.option(
    "-d",
    "--device-id",
    default=None,
    help="Target one device; by default every device is set.",
)
@click.pass_obj
def set_brightness(obj: CliContext, value: int, device_id: str | None) -> None:
    """Set LED brightness 0-100 (the WebUI's slider, /api/brightness/gradual)."""
    if device_id is None:
        channels = fetch_channels(obj.client)
        device_ids = list(dict.fromkeys(c.device_id for c in channels))
        if not device_ids:
            raise click.UsageError("No devices found.")
    else:
        device_ids = [device_id]
    for target in device_ids:
        payload = {"deviceId": target, "brightness": value}
        print_ack(obj.client.post("/api/brightness/gradual", json=payload))
