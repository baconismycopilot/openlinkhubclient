import click

from olh.context import CliContext


@click.group("scheduler")
def scheduler() -> None:
    """Configure the RGB on/off time scheduler."""


@scheduler.command("set-rgb")
@click.option("-e", "--enabled/--disabled", "rgb_control", required=True)
@click.option("-f", "--off-time", "rgb_off", required=True, help='e.g. "22:00"')
@click.option("-n", "--on-time", "rgb_on", required=True, help='e.g. "07:00"')
@click.pass_obj
def set_rgb(obj: CliContext, rgb_control: bool, rgb_off: str, rgb_on: str) -> None:
    """POST /api/scheduler/rgb."""
    payload = {"rgbControl": rgb_control, "rgbOff": rgb_off, "rgbOn": rgb_on}
    obj.render(obj.client.post("/api/scheduler/rgb", json=payload))
