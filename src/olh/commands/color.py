import click

from olh.commands._shared import all_option, path_argument, render_subtree
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
