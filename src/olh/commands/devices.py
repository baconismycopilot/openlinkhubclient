from typing import Any

import click

from olh.commands._resolve import iter_channel_dicts
from olh.commands._shared import path_argument, render_subtree
from olh.context import CliContext


@click.group("devices")
def devices() -> None:
    """Inspect devices and adjust their physical position/label."""


@devices.command("all")
@path_argument
@click.pass_obj
def all_data(obj: CliContext, path: tuple[str, ...]) -> None:
    """Show everything OpenLinkHub knows about (GET /api/).

    PATH drills into the payload one key at a time (case-insensitive), e.g.
    `olh devices all <serial> GetDevice`.
    """
    render_subtree(obj, obj.client.get("/api/"), path, key="device")


@devices.command("list")
@click.pass_obj
def list_devices(obj: CliContext) -> None:
    """List all devices (GET /api/devices/)."""
    response = obj.client.get("/api/devices/")
    if obj.output_format == "table":
        response = _with_channel_summaries(response)
    obj.render(response, key="devices")


def _with_channel_summaries(response: Any) -> Any:
    """Add a synthesized `channels` column ({channelId: "label (description)"})
    next to each device's GetDevice blob, and reduce the GetDevice cell to its
    string-valued keys (manufacturer/product/serial/firmware/...) — the
    structured settings (devices map, profiles, flags) are viewable via
    `devices get <id> [KEY]` instead. Table mode only — -j/-y stay the raw
    envelope."""
    devices_map = response.get("devices") if isinstance(response, dict) else None
    if not isinstance(devices_map, dict):
        return response
    enriched = {}
    for serial, entry in devices_map.items():
        if isinstance(entry, dict):
            entry = _insert_before(entry, "GetDevice", "channels", _channel_summary(entry))
            get_device = entry.get("GetDevice")
            if isinstance(get_device, dict):
                strings_only = {k: v for k, v in get_device.items() if isinstance(v, str)}
                entry["GetDevice"] = strings_only or None
        enriched[serial] = entry
    return {**response, "devices": enriched}


def _channel_summary(entry: dict[str, Any]) -> dict[int, str] | None:
    get_device = entry.get("GetDevice")
    if not isinstance(get_device, dict):
        return None
    summary = {}
    for sub in iter_channel_dicts(get_device):
        label = str(sub.get("label") or sub.get("name") or "")
        description = sub.get("description")
        summary[sub["channelId"]] = f"{label} ({description})" if description else label
    return summary or None


def _insert_before(entry: dict[str, Any], key: str, new_key: str, value: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for existing_key, existing_value in entry.items():
        if existing_key == key:
            out[new_key] = value
        out[existing_key] = existing_value
    out.setdefault(new_key, value)
    return out


@devices.command("get")
@click.argument("device_id")
@path_argument
@click.pass_obj
def get_device(obj: CliContext, device_id: str, path: tuple[str, ...]) -> None:
    """Show one device (GET /api/devices/<device_id>).

    PATH drills into the payload one key at a time (case-insensitive) — the
    structured settings the `devices list` table omits, e.g.
    `devices get <id> devices 1` — and renders just that subtree (-j/-y emit
    it alone, jq-ready).
    """
    render_subtree(obj, obj.client.get(f"/api/devices/{device_id}"), path, key="device")


@devices.command("set-position")
@click.option("-d", "--device-id", required=True)
@click.option("-p", "--position", type=int, required=True)
@click.option("-s", "--device-id-string", required=True, help="The sub-device's own deviceId.")
@click.option("-r", "--direction", type=click.Choice(["left", "right"]), required=True)
@click.pass_obj
def set_position(
    obj: CliContext, device_id: str, position: int, device_id_string: str, direction: str
) -> None:
    """Move a Link Hub sub-device left/right (POST /api/position)."""
    payload = {
        "deviceId": device_id,
        "position": position,
        "deviceIdString": device_id_string,
        "direction": 0 if direction == "left" else 1,
    }
    obj.render(obj.client.post("/api/position", json=payload))


@devices.command("set-label")
@click.option("-d", "--device-id", required=True)
@click.option("-c", "--channel-id", type=int, required=True)
@click.option("-t", "--device-type", type=int, required=True)
@click.option("-l", "--label", required=True)
@click.pass_obj
def set_label(
    obj: CliContext, device_id: str, channel_id: int, device_type: int, label: str
) -> None:
    """Set a device/channel's display label (POST /api/label)."""
    payload = {
        "deviceId": device_id,
        "channelId": channel_id,
        "deviceType": device_type,
        "label": label,
    }
    obj.render(obj.client.post("/api/label", json=payload))
