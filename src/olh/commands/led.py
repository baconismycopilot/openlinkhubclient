import click

from olh.commands._shared import path_argument, render_subtree
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
@path_argument
@click.pass_obj
def get_led(obj: CliContext, device_id: str, path: tuple[str, ...]) -> None:
    """GET /api/led/<device_id>.

    PATH drills into the payload one key at a time (case-insensitive), e.g.
    `olh led get <id> devices 1 channels` for one channel's per-LED colors.
    """
    render_subtree(obj, obj.client.get(f"/api/led/{device_id}"), path, key="data")
