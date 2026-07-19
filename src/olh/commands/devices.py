import click

from olh.context import CliContext


@click.group("devices")
def devices() -> None:
    """Inspect devices and adjust their physical position/label."""


@devices.command("all")
@click.pass_obj
def all_data(obj: CliContext) -> None:
    """Show everything OpenLinkHub knows about (GET /api/)."""
    obj.render(obj.client.get("/api/"), key="device")


@devices.command("list")
@click.pass_obj
def list_devices(obj: CliContext) -> None:
    """List all devices (GET /api/devices/)."""
    obj.render(obj.client.get("/api/devices/"), key="devices")


@devices.command("get")
@click.argument("device_id")
@click.pass_obj
def get_device(obj: CliContext, device_id: str) -> None:
    """Show one device (GET /api/devices/<device_id>)."""
    obj.render(obj.client.get(f"/api/devices/{device_id}"), key="device")


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
