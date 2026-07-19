import click

from olh.context import CliContext


@click.group("speed")
def speed() -> None:
    """Set fan/pump speed profiles or a manual duty cycle."""


@speed.command("set-profile")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-c",
    "--channel-id",
    type=int,
    required=True,
    help="Use 0 to apply the profile to all channels on the device.",
)
@click.option("-p", "--profile", required=True)
@click.pass_obj
def set_profile(obj: CliContext, device_id: str, channel_id: int, profile: str) -> None:
    """POST /api/speed."""
    payload = {"deviceId": device_id, "channelId": channel_id, "profile": profile}
    obj.render(obj.client.post("/api/speed", json=payload))


@speed.command("set-manual")
@click.option("-d", "--device-id", required=True)
@click.option("-c", "--channel-id", type=int, required=True)
@click.option(
    "-v", "--value", type=click.IntRange(0, 100), required=True, help="Duty cycle percent."
)
@click.pass_obj
def set_manual(obj: CliContext, device_id: str, channel_id: int, value: int) -> None:
    """POST /api/speed/manual."""
    payload = {"deviceId": device_id, "channelId": channel_id, "value": value}
    obj.render(obj.client.post("/api/speed/manual", json=payload))
