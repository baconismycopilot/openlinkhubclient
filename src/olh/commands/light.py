import click

from olh.commands._resolve import (
    fetch_channels,
    resolve_rgb_profile,
    resolve_targets,
    rgb_profiles_by_device,
)
from olh.commands._shared import COLOR, exit_if_write_failed
from olh.commands.color import build_rgb_profile_payload
from olh.context import CliContext


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
    ok = True
    for device_id, channel_id, canonical in resolved:
        payload = {"deviceId": device_id, "channelId": channel_id, "profile": canonical}
        ok = obj.ack(obj.client.post("/api/color", json=payload)) and ok
    exit_if_write_failed(ok)


@light.command("color")
@click.argument("color", type=COLOR)
@click.option(
    "-p",
    "--profile",
    default="static",
    show_default=True,
    help="Which stored profile to recolor and activate.",
)
@click.option(
    "-d",
    "--device-id",
    default=None,
    help="Target one device; by default every device with that profile is set.",
)
@click.option(
    "--no-apply",
    is_flag=True,
    default=False,
    help="Only recolor the stored profile; don't activate it on the channels.",
)
@click.option(
    "--speed",
    type=click.FloatRange(1, 10),
    default=None,
    help="Animation speed 1-10. Needed when the stored profile has one outside "
    "that range (the stock 'off' and 'led' profiles store 0), which the server rejects.",
)
@click.pass_obj
def set_color(
    obj: CliContext,
    color: dict[str, int],
    profile: str,
    device_id: str | None,
    no_apply: bool,
    speed: float | None,
) -> None:
    """Set the lighting to a specific color: `light color '#ff00ff'`.

    An RGB profile stores the color and `light set` only picks which profile is
    active, so a literal color takes two calls — recolor the profile, then
    activate it. This does both. The color is stored per device *and profile*,
    not per channel, so every channel using that profile takes the new color;
    for one channel only, the API's per-channel override is a separate feature.
    """
    by_device = rgb_profiles_by_device(obj.client)
    if device_id is not None:
        if device_id not in by_device:
            available = ", ".join(sorted(by_device)) or "none"
            raise click.UsageError(f"Unknown device {device_id!r}. Known devices: {available}.")
        by_device = {device_id: by_device[device_id]}
    targets = [
        (dev, next((p for p in profiles if p.casefold() == profile.casefold()), None))
        for dev, profiles in by_device.items()
    ]
    targets = [(dev, canonical) for dev, canonical in targets if canonical is not None]
    if not targets:
        raise click.UsageError(f"No device has an RGB profile named {profile!r}.")
    # Read and validate every device's profile before writing to any of them,
    # so a device the server would reject can't leave the earlier ones already
    # recolored and the hubs mismatched — the same invariant `light set` keeps.
    writes = [
        (
            target,
            canonical,
            build_rgb_profile_payload(
                obj, target, canonical, start=color, middle=color, end=color, speed=speed
            ),
        )
        for target, canonical in targets
    ]
    ok = True
    for target, canonical, payload in writes:
        if not obj.ack(obj.client.put("/api/color/change", json=payload)):
            # The recolor failed server-side (often as a 200 envelope the
            # client doesn't raise on), so activating the profile now would
            # just re-apply the *old* color and call it a success.
            ok = False
            continue
        if no_apply:
            continue
        activation = {"deviceId": target, "channelId": -1, "profile": canonical}
        ok = obj.ack(obj.client.post("/api/color", json=activation)) and ok
    exit_if_write_failed(ok)


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
    ok = True
    for target in device_ids:
        payload = {"deviceId": target, "brightness": value}
        ok = obj.ack(obj.client.post("/api/brightness/gradual", json=payload)) and ok
    exit_if_write_failed(ok)
