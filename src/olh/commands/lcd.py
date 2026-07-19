import click

from olh.context import CliContext


@click.group("lcd")
def lcd() -> None:
    """Configure LCD screens: device assignment, image, rotation, profile."""


@lcd.command("set-device")
@click.option("-d", "--device-id", required=True)
@click.option("-c", "--channel-id", type=int, required=True)
@click.option("-t", "--device-type", type=int, required=True)
@click.option("-l", "--lcd-serial", required=True)
@click.pass_obj
def set_device(
    obj: CliContext, device_id: str, channel_id: int, device_type: int, lcd_serial: str
) -> None:
    """POST /api/lcd/device. Link System Hub multi-LCD setup."""
    payload = {
        "deviceId": device_id,
        "channelId": channel_id,
        "deviceType": device_type,
        "lcdSerial": lcd_serial,
    }
    obj.render(obj.client.post("/api/lcd/device", json=payload))


@lcd.command("set-image")
@click.option("-d", "--device-id", required=True)
@click.option("-c", "--channel-id", type=int, required=True)
@click.option("-i", "--image", required=True, help="Name of an uploaded animation image/gif.")
@click.pass_obj
def set_image(obj: CliContext, device_id: str, channel_id: int, image: str) -> None:
    """POST /api/lcd/image."""
    payload = {"deviceId": device_id, "channelId": channel_id, "image": image}
    obj.render(obj.client.post("/api/lcd/image", json=payload))


@lcd.command("set-rotation")
@click.option("-d", "--device-id", required=True)
@click.option("-c", "--channel-id", type=int, required=True)
@click.option(
    "-g", "--degrees", "rotation", type=click.Choice(["0", "90", "180", "270"]), required=True
)
@click.pass_obj
def set_rotation(obj: CliContext, device_id: str, channel_id: int, rotation: str) -> None:
    """POST /api/lcd/rotation."""
    code = {"0": 0, "90": 1, "180": 2, "270": 3}[rotation]
    payload = {"deviceId": device_id, "channelId": channel_id, "rotation": code}
    obj.render(obj.client.post("/api/lcd/rotation", json=payload))


@lcd.command("set-profile")
@click.option("-d", "--device-id", required=True)
@click.option("-p", "--profile", required=True)
@click.pass_obj
def set_profile(obj: CliContext, device_id: str, profile: str) -> None:
    """POST /api/lcd/profile."""
    payload = {"deviceId": device_id, "profile": profile}
    obj.render(obj.client.post("/api/lcd/profile", json=payload))
