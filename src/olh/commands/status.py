import click

from olh.commands._resolve import fetch_channels
from olh.context import CliContext


@click.command("status")
@click.pass_obj
def status(obj: CliContext) -> None:
    """One-table dashboard of every channel: speed profile, RPM, temperature, RGB."""
    rows = [
        {
            "label": c.label,
            "type": c.description,
            "profile": c.profile,
            "rpm": c.rpm,
            "temperature": c.temperature,
            "rgb": c.rgb,
            "device": c.device_id,
        }
        for c in fetch_channels(obj.client)
    ]
    obj.render(rows)
