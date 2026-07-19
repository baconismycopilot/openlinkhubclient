import click

from olh.context import CliContext


@click.group("headset")
def headset() -> None:
    """Headset sleep, mute indicator, ANC, and sidetone settings."""


@headset.command("set-sleep")
@click.option("-d", "--device-id", required=True)
@click.option("-m", "--minutes", "sleep_mode", type=int, required=True)
@click.pass_obj
def set_sleep(obj: CliContext, device_id: str, sleep_mode: int) -> None:
    """POST /api/headset/sleep."""
    payload = {"deviceId": device_id, "sleepMode": sleep_mode}
    obj.render(obj.client.post("/api/headset/sleep", json=payload))


@headset.command("set-mute-indicator")
@click.option("-d", "--device-id", required=True)
@click.option("-e", "--enabled/--disabled", "enabled", required=True)
@click.pass_obj
def set_mute_indicator(obj: CliContext, device_id: str, enabled: bool) -> None:
    """POST /api/headset/muteIndicator."""
    payload = {"deviceId": device_id, "muteIndicator": int(enabled)}
    obj.render(obj.client.post("/api/headset/muteIndicator", json=payload))


@headset.command("set-anc")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-m",
    "--mode",
    "noise_cancellation",
    type=click.Choice(["off", "on", "transparency"]),
    required=True,
    help="Requires Sidetone to be off.",
)
@click.pass_obj
def set_anc(obj: CliContext, device_id: str, noise_cancellation: str) -> None:
    """POST /api/headset/anc."""
    code = {"off": 0, "on": 1, "transparency": 2}[noise_cancellation]
    payload = {"deviceId": device_id, "noiseCancellation": code}
    obj.render(obj.client.post("/api/headset/anc", json=payload))


@headset.command("set-sidetone")
@click.option("-d", "--device-id", required=True)
@click.option(
    "-e", "--enabled/--disabled", "enabled", required=True, help="Requires ANC to be off."
)
@click.pass_obj
def set_sidetone(obj: CliContext, device_id: str, enabled: bool) -> None:
    """POST /api/headset/sidetone."""
    payload = {"deviceId": device_id, "sideTone": int(enabled)}
    obj.render(obj.client.post("/api/headset/sidetone", json=payload))


@headset.command("set-sidetone-value")
@click.option("-d", "--device-id", required=True)
@click.option("-v", "--value", "side_tone_value", type=click.IntRange(0, 100), required=True)
@click.pass_obj
def set_sidetone_value(obj: CliContext, device_id: str, side_tone_value: int) -> None:
    """POST /api/headset/sidetoneValue. Requires Sidetone to be on."""
    payload = {"deviceId": device_id, "sideToneValue": side_tone_value}
    obj.render(obj.client.post("/api/headset/sidetoneValue", json=payload))
