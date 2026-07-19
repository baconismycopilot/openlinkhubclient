import click

from olh.commands._shared import rgb_options, yes_option
from olh.context import CliContext
from olh.output import confirm_or_abort


@click.group("keyboard")
def keyboard() -> None:
    """Keyboard profile, layout, and per-key device settings."""


@keyboard.command("set-profile")
@click.option("-d", "--device-id", required=True)
@click.option("-n", "--profile-name", "keyboard_profile_name", required=True)
@click.pass_obj
def set_profile(obj: CliContext, device_id: str, keyboard_profile_name: str) -> None:
    """POST /api/keyboard/profile/change."""
    payload = {"deviceId": device_id, "keyboardProfileName": keyboard_profile_name}
    obj.render(obj.client.post("/api/keyboard/profile/change", json=payload))


@keyboard.command("save-profile")
@click.option("-d", "--device-id", required=True)
@click.option("-n", "--profile-name", "keyboard_profile_name", required=True)
@click.option("-N", "--new", "is_new", is_flag=True, help="Save this as a brand new profile.")
@click.pass_obj
def save_profile(obj: CliContext, device_id: str, keyboard_profile_name: str, is_new: bool) -> None:
    """PUT /api/keyboard/profile/new."""
    payload = {
        "deviceId": device_id,
        "keyboardProfileName": keyboard_profile_name,
        "new": is_new,
    }
    obj.render(obj.client.put("/api/keyboard/profile/new", json=payload))


@keyboard.command("delete-profile")
@click.option("-d", "--device-id", required=True)
@click.option("-n", "--profile-name", "keyboard_profile_name", required=True)
@yes_option
@click.pass_obj
def delete_profile(obj: CliContext, device_id: str, keyboard_profile_name: str, yes: bool) -> None:
    """DELETE /api/keyboard/profile/delete."""
    confirm_or_abort(f"Delete keyboard profile {keyboard_profile_name!r}?", yes=yes)
    payload = {"deviceId": device_id, "keyboardProfileName": keyboard_profile_name}
    obj.render(obj.client.delete("/api/keyboard/profile/delete", json=payload))


@keyboard.command("set-layout")
@click.option("-d", "--device-id", required=True)
@click.option("-l", "--layout", "keyboard_layout", required=True, help='e.g. "US", "UK", "DE"')
@yes_option
@click.pass_obj
def set_layout(obj: CliContext, device_id: str, keyboard_layout: str, yes: bool) -> None:
    """POST /api/keyboard/layout."""
    confirm_or_abort(f"Change the physical keyboard layout to {keyboard_layout!r}?", yes=yes)
    payload = {"deviceId": device_id, "keyboardLayout": keyboard_layout}
    obj.render(obj.client.post("/api/keyboard/layout", json=payload))


@keyboard.command("set-dial")
@click.option("-d", "--device-id", required=True)
@click.option("-D", "--dial", "keyboard_control_dial", type=int, required=True)
@click.pass_obj
def set_dial(obj: CliContext, device_id: str, keyboard_control_dial: int) -> None:
    """POST /api/keyboard/dial."""
    payload = {"deviceId": device_id, "keyboardControlDial": keyboard_control_dial}
    obj.render(obj.client.post("/api/keyboard/dial", json=payload))


@keyboard.command("set-sleep")
@click.option("-d", "--device-id", required=True)
@click.option("-m", "--minutes", "sleep_mode", type=int, required=True)
@click.pass_obj
def set_sleep(obj: CliContext, device_id: str, sleep_mode: int) -> None:
    """POST /api/keyboard/sleep."""
    payload = {"deviceId": device_id, "sleepMode": sleep_mode}
    obj.render(obj.client.post("/api/keyboard/sleep", json=payload))


@keyboard.command("set-polling-rate")
@click.option("-d", "--device-id", required=True)
@click.option("-r", "--rate", "polling_rate", type=int, required=True)
@click.pass_obj
def set_polling_rate(obj: CliContext, device_id: str, polling_rate: int) -> None:
    """POST /api/keyboard/pollingRate."""
    payload = {"deviceId": device_id, "pollingRate": polling_rate}
    obj.render(obj.client.post("/api/keyboard/pollingRate", json=payload))


@keyboard.command("set-color")
@click.option("-d", "--device-id", required=True)
@click.option("-k", "--key-id", type=int, required=True)
@click.option(
    "-s",
    "--scope",
    "key_option",
    type=click.Choice(["key", "row", "all"]),
    required=True,
)
@rgb_options
@click.pass_obj
def set_color(
    obj: CliContext,
    device_id: str,
    key_id: int,
    key_option: str,
    red: int,
    green: int,
    blue: int,
) -> None:
    """POST /api/keyboard/color."""
    scope_code = {"key": 0, "row": 1, "all": 2}[key_option]
    payload = {
        "deviceId": device_id,
        "keyId": key_id,
        "keyOption": scope_code,
        "color": {"red": red, "green": green, "blue": blue},
    }
    obj.render(obj.client.post("/api/keyboard/color", json=payload))
