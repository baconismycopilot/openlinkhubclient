import click

from olh.commands._resolve import (
    fetch_channels,
    parse_speed_value,
    resolve_speed_profile,
    resolve_targets,
)
from olh.context import CliContext
from olh.output import print_ack


@click.group("fan")
def fan() -> None:
    """Set fan/pump speeds by channel label instead of raw device/channel ids."""


@fan.command("list")
@click.pass_obj
def list_fans(obj: CliContext) -> None:
    """Every speed-capable channel with its current profile, RPM and temperature."""
    channels = [c for c in fetch_channels(obj.client) if c.has_speed]
    rows = [
        {
            "label": c.label,
            "channel": c.channel_id,
            "type": c.description,
            "profile": c.profile,
            "rpm": c.rpm,
            "temperature": c.temperature,
            "device": c.device_id,
        }
        for c in channels
    ]
    obj.render(rows)


@fan.command("set")
@click.argument("name")
@click.argument("value")
@click.pass_obj
def set_fan(obj: CliContext, name: str, value: str) -> None:
    """Set NAME (a channel label, "pump", a channel id, or "all") to VALUE.

    VALUE is either a fixed duty cycle ("50%" or "50" — needs the daemon's
    `manual: true` config) or a named speed profile ("quiet", "performance").
    """
    duty = parse_speed_value(value)
    channels = [c for c in fetch_channels(obj.client) if c.has_speed]
    if not channels:
        raise click.UsageError("No speed-capable channels found on any device.")
    targets = resolve_targets(channels, name)
    if duty is not None:
        for device_id, channel_id in targets:
            payload = {"deviceId": device_id, "channelId": channel_id, "value": duty}
            print_ack(obj.client.post("/api/speed/manual", json=payload))
    else:
        profile = resolve_speed_profile(obj.client, value)
        for device_id, channel_id in targets:
            payload = {"deviceId": device_id, "channelId": channel_id, "profile": profile}
            print_ack(obj.client.post("/api/speed", json=payload))
