import click

from olh.context import CliContext


@click.group("psu")
def psu() -> None:
    """Configure PSU fan speed mode."""


@psu.command("set-speed")
@click.option("-d", "--device-id", required=True)
@click.option("-f", "--fan-mode", type=int, required=True)
@click.pass_obj
def set_speed(obj: CliContext, device_id: str, fan_mode: int) -> None:
    """POST /api/psu/speed."""
    payload = {"deviceId": device_id, "fanMode": fan_mode}
    obj.render(obj.client.post("/api/psu/speed", json=payload))
