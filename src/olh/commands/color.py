from typing import Any

import click

from olh.commands._shared import (
    COLOR,
    all_option,
    exit_if_write_failed,
    path_argument,
    render_subtree,
)
from olh.context import CliContext


@click.group("color")
def color() -> None:
    """Read and set device RGB profiles."""


@color.command("list")
@click.pass_obj
def list_colors(obj: CliContext) -> None:
    """GET /api/color/."""
    obj.render(obj.client.get("/api/color/"), key="data")


@color.command("get")
@click.argument("device_id")
@path_argument
@all_option
@click.pass_obj
def get_color(obj: CliContext, device_id: str, path: tuple[str, ...], show_all: bool) -> None:
    """GET /api/color/<device_id>.

    PATH drills into the payload one key at a time (case-insensitive), e.g.
    `olh color get <id> profiles rainbow`; --all renders every nested table.
    """
    render_subtree(
        obj, obj.client.get(f"/api/color/{device_id}"), path, key="data", expand=show_all
    )


@color.command("set")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-c",
    "--channel-id",
    type=int,
    required=True,
    help="Use -1 to apply the profile to all channels on the device.",
)
@click.option("-p", "--profile", required=True)
@click.pass_obj
def set_color(obj: CliContext, device_id: str, channel_id: int, profile: str) -> None:
    """POST /api/color."""
    payload = {"deviceId": device_id, "channelId": channel_id, "profile": profile}
    obj.render(obj.client.post("/api/color", json=payload))


def _triplet(color: Any) -> dict[str, int]:
    """Reduce a stored profile color (red/green/blue plus brightness, position,
    temperature, Hex) to the three channels the update endpoint validates."""
    if not isinstance(color, dict):
        return {"red": 0, "green": 0, "blue": 0}
    return {channel: int(color.get(channel) or 0) for channel in ("red", "green", "blue")}


def build_rgb_profile_payload(
    obj: CliContext,
    device_id: str,
    profile: str,
    *,
    start: dict[str, int] | None = None,
    middle: dict[str, int] | None = None,
    end: dict[str, int] | None = None,
    speed: float | None = None,
) -> dict[str, Any]:
    """The read-modify half of the read-modify-write below: GET one device's
    stored RGB profile and build the full PUT /api/color/change body from it.

    The endpoint is a full replace, not a patch: it rebuilds the profile from
    the request body alone, so every field left out reverts to its zero value
    (the same trap as `dashboard update` — see CLAUDE.md). We GET the profile
    first and overlay only what the caller passed. The stored profile and the
    request body also use different names for the same fields
    (start/minTemp/gradients vs startColor/rgbMinTemp/colorZones), so this is
    where that mapping lives.

    Kept separate from the write so a caller changing several devices can
    validate all of them before writing any (see `light color`) — every
    failure mode here is a UsageError raised before a single byte is sent."""
    envelope = obj.client.get(f"/api/color/{device_id}")
    data = envelope.get("data") if isinstance(envelope, dict) else None
    profiles = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles, dict) or not profiles:
        raise click.UsageError(f"Device {device_id} reports no RGB profiles.")
    matches = [name for name in profiles if name.casefold() == profile.casefold()]
    if not matches:
        available = ", ".join(sorted(profiles))
        raise click.UsageError(
            f"No RGB profile {profile!r} on device {device_id}. Available: {available}."
        )
    if len(matches) > 1:
        # The payload really does mix casings, so a fold collision is possible;
        # picking one silently would edit an arbitrary profile's colors.
        candidates = ", ".join(repr(name) for name in sorted(matches))
        raise click.UsageError(
            f"{profile!r} is ambiguous on device {device_id}: matches {candidates}. "
            "Pass the exact name."
        )
    canonical = matches[0]
    current = profiles[canonical]
    if not isinstance(current, dict):
        raise click.UsageError(
            f"Profile {canonical!r} on device {device_id} is {current!r}, not an object."
        )

    resolved_speed = current.get("speed") if speed is None else speed
    if not isinstance(resolved_speed, int | float) or not 1 <= resolved_speed <= 10:
        raise click.UsageError(
            f"Profile {canonical!r} has speed {resolved_speed!r}, which the server rejects "
            "(it requires 1-10). Pass --speed explicitly to set a valid one."
        )

    payload = {
        "deviceId": device_id,
        "profile": canonical,
        "startColor": _triplet(current.get("start")) if start is None else start,
        "middleColor": _triplet(current.get("middle")) if middle is None else middle,
        "endColor": _triplet(current.get("end")) if end is None else end,
        "speed": resolved_speed,
        "rgbMinTemp": current.get("minTemp") or 0,
        "rgbMaxTemp": current.get("maxTemp") or 0,
        "alternateColors": bool(current.get("alternateColors")),
        "rgbDirection": current.get("rgbDirection") or 0,
        "colorZones": current.get("gradients"),
    }
    return payload


def change_rgb_profile(
    obj: CliContext,
    device_id: str,
    profile: str,
    *,
    start: dict[str, int] | None = None,
    middle: dict[str, int] | None = None,
    end: dict[str, int] | None = None,
    speed: float | None = None,
) -> Any:
    """Read-modify-write one device's stored RGB profile via PUT
    /api/color/change."""
    payload = build_rgb_profile_payload(
        obj, device_id, profile, start=start, middle=middle, end=end, speed=speed
    )
    return obj.client.put("/api/color/change", json=payload)


@color.command("change")
@click.option("-d", "--device-id", required=True)
@click.option("-p", "--profile", required=True, help="Which stored profile to edit, e.g. static.")
@click.option("-s", "--start", type=COLOR, default=None, help="'#rrggbb', '#rgb', or 'r,g,b'.")
@click.option("-m", "--middle", type=COLOR, default=None)
@click.option("-e", "--end", type=COLOR, default=None)
@click.option("--speed", type=click.FloatRange(1, 10), default=None)
@click.pass_obj
def change_color(
    obj: CliContext,
    device_id: str,
    profile: str,
    start: dict[str, int] | None,
    middle: dict[str, int] | None,
    end: dict[str, int] | None,
    speed: float | None,
) -> None:
    """PUT /api/color/change: edit a stored profile's colors.

    `color set` only picks which profile is active — the color itself lives in
    the profile. To make channels a specific color, set `static`'s colors here
    and activate it with `color set`/`light set` (or use `light color`, which
    does both).
    """
    exit_if_write_failed(
        obj.ack(
            change_rgb_profile(
                obj, device_id, profile, start=start, middle=middle, end=end, speed=speed
            )
        )
    )
