import click

from olh.context import CliContext


@click.group("media")
def media() -> None:
    """Read current media playback status via MPRIS."""


@media.command("playback")
@click.pass_obj
def playback(obj: CliContext) -> None:
    """GET /api/media/playback. Requires the service to run in user-context mode."""
    obj.render(obj.client.get("/api/media/playback"), key="data")
