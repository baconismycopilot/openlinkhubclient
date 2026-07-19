import click

from olh.context import CliContext


@click.group("brightness")
def brightness() -> None:
    """Set device brightness, either from the preset dropdown or a 0-100 slider."""


@brightness.command("set")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-l",
    "--level",
    "brightness_value",
    type=click.Choice(["100", "66", "33", "0"]),
    required=True,
    help="Dropdown preset (100/66/33/0), mapped to OpenLinkHub's 0-3 codes.",
)
@click.pass_obj
def set_brightness(obj: CliContext, device_id: str, brightness_value: str) -> None:
    """POST /api/brightness."""
    code = {"100": 0, "66": 1, "33": 2, "0": 3}[brightness_value]
    payload = {"deviceId": device_id, "brightness": code}
    obj.render(obj.client.post("/api/brightness", json=payload))


@brightness.command("set-gradual")
@click.option("-d", "--device-id", required=True)
@click.option("-p", "--percent", "brightness_value", type=click.IntRange(0, 100), required=True)
@click.pass_obj
def set_gradual(obj: CliContext, device_id: str, brightness_value: int) -> None:
    """POST /api/brightness/gradual. Slider-style, any value 0-100."""
    payload = {"deviceId": device_id, "brightness": brightness_value}
    obj.render(obj.client.post("/api/brightness/gradual", json=payload))
