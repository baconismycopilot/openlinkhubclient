import click

from olh.context import CliContext


@click.group("led")
def led() -> None:
    """Read per-channel LED state."""


@led.command("list")
@click.pass_obj
def list_led(obj: CliContext) -> None:
    """GET /api/led/."""
    obj.render(obj.client.get("/api/led/"), key="data")


@led.command("get")
@click.argument("device_id")
@click.pass_obj
def get_led(obj: CliContext, device_id: str) -> None:
    """GET /api/led/<device_id>."""
    obj.render(obj.client.get(f"/api/led/{device_id}"), key="data")
