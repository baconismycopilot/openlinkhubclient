import click

from olh.context import CliContext


@click.group("input-keys")
def input_keys() -> None:
    """Look up valid key/command codes for macros and key assignments."""


@input_keys.command("media")
@click.pass_obj
def media(obj: CliContext) -> None:
    """GET /api/input/media."""
    obj.render(obj.client.get("/api/input/media"), key="data")


@input_keys.command("keyboard")
@click.pass_obj
def keyboard(obj: CliContext) -> None:
    """GET /api/input/keyboard."""
    obj.render(obj.client.get("/api/input/keyboard"), key="data")


@input_keys.command("mouse")
@click.pass_obj
def mouse(obj: CliContext) -> None:
    """GET /api/input/mouse."""
    obj.render(obj.client.get("/api/input/mouse"), key="data")
