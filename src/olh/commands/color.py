import click

from olh.commands._shared import render_subtree
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
@click.argument("path", nargs=-1)
@click.pass_obj
def get_color(obj: CliContext, device_id: str, path: tuple[str, ...]) -> None:
    """GET /api/color/<device_id>.

    PATH drills into the payload one key at a time (case-insensitive), e.g.
    `olh color get <id> profiles rainbow`.
    """
    render_subtree(obj, obj.client.get(f"/api/color/{device_id}"), path, key="data")


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
