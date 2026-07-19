import click

from olh.commands._shared import JSON
from olh.context import CliContext


@click.group("mouse")
def mouse() -> None:
    """Mouse DPI, RGB zones, sleep, polling rate, and button assignments."""


@mouse.command("set-dpi")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-s",
    "--stages",
    type=JSON,
    required=True,
    help='JSON object of stage index -> DPI, e.g. \'{"0":800,"1":1600}\'',
)
@click.pass_obj
def set_dpi(obj: CliContext, device_id: str, stages: dict) -> None:
    """POST /api/mouse/dpi."""
    obj.render(obj.client.post("/api/mouse/dpi", json={"deviceId": device_id, "stages": stages}))


@mouse.command("set-dpi-colors")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-c",
    "--color-zones",
    type=JSON,
    required=True,
    help='JSON object of zone index -> {"red","green","blue"}',
)
@click.pass_obj
def set_dpi_colors(obj: CliContext, device_id: str, color_zones: dict) -> None:
    """POST /api/mouse/dpiColors."""
    payload = {"deviceId": device_id, "colorZones": color_zones}
    obj.render(obj.client.post("/api/mouse/dpiColors", json=payload))


@mouse.command("set-zone-colors")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-c",
    "--color-zones",
    type=JSON,
    required=True,
    help='JSON object of zone index -> {"red","green","blue"}',
)
@click.pass_obj
def set_zone_colors(obj: CliContext, device_id: str, color_zones: dict) -> None:
    """POST /api/mouse/zoneColors."""
    payload = {"deviceId": device_id, "colorZones": color_zones}
    obj.render(obj.client.post("/api/mouse/zoneColors", json=payload))


@mouse.command("set-sleep")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-m",
    "--minutes",
    "sleep_mode",
    type=click.Choice(["1", "5", "10", "15", "30", "60"]),
    required=True,
)
@click.pass_obj
def set_sleep(obj: CliContext, device_id: str, sleep_mode: str) -> None:
    """POST /api/mouse/sleep."""
    payload = {"deviceId": device_id, "sleepMode": int(sleep_mode)}
    obj.render(obj.client.post("/api/mouse/sleep", json=payload))


@mouse.command("set-polling-rate")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-r",
    "--rate",
    "polling_rate",
    type=click.Choice(["125", "250", "500", "1000"]),
    required=True,
    help="Hz; mapped to OpenLinkHub's 1-4 polling rate codes.",
)
@click.pass_obj
def set_polling_rate(obj: CliContext, device_id: str, polling_rate: str) -> None:
    """POST /api/mouse/pollingRate."""
    code = {"125": 1, "250": 2, "500": 3, "1000": 4}[polling_rate]
    payload = {"deviceId": device_id, "pollingRate": code}
    obj.render(obj.client.post("/api/mouse/pollingRate", json=payload))


@mouse.command("set-angle-snapping")
@click.option("-d", "--device-id", required=True)
@click.option("-e", "--enabled/--disabled", "enabled", required=True)
@click.pass_obj
def set_angle_snapping(obj: CliContext, device_id: str, enabled: bool) -> None:
    """POST /api/mouse/angleSnapping."""
    payload = {"deviceId": device_id, "angleSnapping": int(enabled)}
    obj.render(obj.client.post("/api/mouse/angleSnapping", json=payload))


@mouse.command("set-button-optimization")
@click.option("-d", "--device-id", required=True)
@click.option("-e", "--enabled/--disabled", "enabled", required=True)
@click.pass_obj
def set_button_optimization(obj: CliContext, device_id: str, enabled: bool) -> None:
    """POST /api/mouse/buttonOptimization."""
    payload = {"deviceId": device_id, "buttonOptimization": int(enabled)}
    obj.render(obj.client.post("/api/mouse/buttonOptimization", json=payload))


@mouse.command("set-key-assignment")
@click.option("-d", "--device-id", required=True)
@click.option("-k", "--key-index", type=int, required=True)
@click.option("-e", "--enabled/--disabled", "enabled", default=True)
@click.option("-p", "--press-and-hold/--no-press-and-hold", "press_and_hold", default=False)
@click.option("-t", "--assignment-type", "key_assignment_type", type=int, required=True)
@click.option("-v", "--assignment-value", "key_assignment_value", type=int, required=True)
@click.pass_obj
def set_key_assignment(
    obj: CliContext,
    device_id: str,
    key_index: int,
    enabled: bool,
    press_and_hold: bool,
    key_assignment_type: int,
    key_assignment_value: int,
) -> None:
    """POST /api/mouse/updateKeyAssignment."""
    payload = {
        "deviceId": device_id,
        "keyIndex": key_index,
        "enabled": enabled,
        "pressAndHold": press_and_hold,
        "keyAssignmentType": key_assignment_type,
        "keyAssignmentValue": key_assignment_value,
    }
    obj.render(obj.client.post("/api/mouse/updateKeyAssignment", json=payload))
